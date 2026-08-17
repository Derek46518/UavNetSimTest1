import random
from simulator.log import logger
from utils import config
from utils.util_function import euclidean_distance_3d
from routing.macg.macg_packet import MACGControlPacket

# ---------------------------------------------------------------------- #
# Node roles (section 8 of the spec)
# ---------------------------------------------------------------------- #
ROLE_UNCLUSTERED = 0
ROLE_CH = 1
ROLE_GW = 2
ROLE_CM = 3


class MACGClusterManager:
    """
    Owns MACG clustering state and clustering control logic (role, cluster id, CH id, cluster
    epoch, nomination state, CH election/fallback, cluster joining, member table, gateway
    discovery/table, maintenance, member/CH timeout, re-association, cluster diagnostics).

    This class performs the full clustering *state machine*: bootstrap -> neighbor discovery ->
    nomination -> CH declaration (+ fallback) -> join -> active cluster -> maintenance /
    re-association (section 13 of the spec). It also sends every MACG clustering control packet
    (NOMINATION, CH_DECLARE, JOIN_REQUEST, JOIN_ACCEPT, CLUSTER_STATE, MAINTENANCE,
    MAINT_RESPONSE, GATEWAY_UPDATE) itself, counting each one as routing control traffic.

    All decisions here are made from local state, received control packets, and the local
    neighbor table only -- never by inspecting another drone's live cluster-manager state.

    The data-plane (DataPacket next-hop selection, ACK handling, Greedy forwarding) lives in
    "macg.py" and only reads the small amount of public state exposed here (role, cluster_id,
    cluster_head_id, cluster_head_position, member_table, gateway_table, ...); it does not
    duplicate this state machine.
    """

    def __init__(self, simulator, my_drone, neighbor_table):
        self.simulator = simulator
        self.my_drone = my_drone
        self.env = simulator.env
        self.neighbor_table = neighbor_table
        self.rng = random.Random(my_drone.identifier + simulator.seed + 20)

        # --- own clustering state (section 8) --- #
        self.role = ROLE_UNCLUSTERED
        self.cluster_id = None
        self.cluster_head_id = None
        self.cluster_epoch = 0
        self.cluster_head_position = None
        self.cluster_head_velocity = None

        # --- nomination state (section 15) --- #
        self.nomination_count = 0
        self.nominators = set()
        self._collecting_nominations = False

        # --- visible CH declarations, keyed by CH id (sections 16, 18, 29) --- #
        self.visible_CHs = {}

        # --- CH-only state (sections 21, 24) --- #
        self.member_table = {}  # member_id -> {last_response_time, position, velocity, residual_energy, miss_count, responded}
        self.member_external_links = {}  # member_id -> {neighbor_cluster_id: {external_neighbor_id, external_neighbor_position, similarity, count}}
        self.gateway_table = {}  # neighbor_cluster_id -> {local_gateway_id, external_neighbor_id, external_neighbor_position, cross_link_count, cross_link_similarity, gateway_energy, last_update_time}

        # --- member-side caches --- #
        self.known_cluster_members = set()  # optional cache from CLUSTER_STATE (section 19)
        self._reported_clusters = set()  # neighbor cluster ids already GATEWAY_UPDATE-reported this "epoch" of visibility
        self._maintenance_received_this_round = False
        self._ch_miss_count = 0
        self._pending_join_ch = None
        self._join_accept_event = None

        # --- protocol-local diagnostics (section 55) --- #
        self.diagnostics = {
            'join_attempts': 0,
            'successful_joins': 0,
            're_associations': 0,
            'member_removals': 0,
            'gateway_changes': 0,
            'ch_declarations': 0,
            'flat_greedy_fallback_count': 0,
            'hierarchical_forward_count': 0,
        }

    def start(self):
        self.env.process(self._lifecycle())

    def is_member(self, drone_id):
        """True if "drone_id" is known (by this CH) to belong to this cluster"""
        return drone_id == self.my_drone.identifier or drone_id in self.member_table

    # ================================================================== #
    # cluster formation state machine (sections 13-21, 29)
    # ================================================================== #

    def _lifecycle(self):
        is_bootstrap = True
        while True:
            joined = yield self.env.process(self._formation_cycle(is_bootstrap))
            is_bootstrap = False

            if joined:
                if self.role == ROLE_CH:
                    yield self.env.process(self._ch_active_loop())  # runs forever for a CH
                else:
                    yield self.env.process(self._member_active_loop())  # returns once CH is lost
                # falls through here only after CH loss -> immediately re-run formation
            else:
                # defensive fallback: should not normally happen since _formation_cycle always
                # ends in either a CH declaration, a successful join or a singleton CH fallback
                yield self.env.timeout(self.rng.randint(1000, 5000))

    def _formation_cycle(self, is_bootstrap):
        self.role = ROLE_UNCLUSTERED
        self.cluster_id = None
        self.cluster_head_id = None
        self.cluster_head_position = None
        self.cluster_head_velocity = None
        self.cluster_epoch += 1
        self.nomination_count = 0
        self.nominators = set()
        self.known_cluster_members = set()
        self._collecting_nominations = True

        if is_bootstrap:
            jitter = self.rng.randint(0, 50000)
            yield self.env.timeout(config.MACG_BOOTSTRAP_DELAY + jitter)

        self.neighbor_table.purge()

        # --- NOMINATION (section 15) --- #
        target_id = self.neighbor_table.best_similarity_neighbor()
        if target_id is not None:
            self._send_nomination(target_id)

        yield self.env.timeout(config.MACG_NOMINATION_WINDOW)
        self._collecting_nominations = False

        # --- CH DECLARATION (section 16) --- #
        if self.role == ROLE_UNCLUSTERED and self.nomination_count >= config.MACG_NOMINATION_THRESHOLD:
            self._become_ch()

        yield self.env.timeout(config.MACG_CH_DECLARATION_WINDOW)

        if self.role == ROLE_CH:
            return True

        # --- CH FALLBACK ELECTION (section 17), only needed if no CH is visible yet --- #
        if not self._collect_visible_ch_candidates():
            elected = self._attempt_fallback_election()
            if elected:
                return True

            # give the actual (deterministic) winner among our neighbors a short grace period to
            # broadcast its CH_DECLARE before giving up on this round entirely
            yield self.env.timeout(config.MACG_CH_DECLARATION_WINDOW)
            if self.role == ROLE_CH:
                return True

        # --- JOIN (sections 18-20) --- #
        joined = yield self.env.process(self._attempt_join_sequence())
        return joined

    def _become_ch(self):
        self.role = ROLE_CH
        self.cluster_id = self.my_drone.identifier
        self.cluster_head_id = self.my_drone.identifier
        self.cluster_head_position = list(self.my_drone.coords)
        self.cluster_head_velocity = list(self.my_drone.velocity)
        self.member_table = {}
        self.member_external_links = {}
        self.gateway_table = {}
        self.known_cluster_members = {self.my_drone.identifier}
        self.diagnostics['ch_declarations'] += 1

        logger.info('At time: %s (us) ---- UAV: %s becomes MACG cluster head (epoch %s)',
                    self.env.now, self.my_drone.identifier, self.cluster_epoch)

        payload = {
            'ch_id': self.my_drone.identifier,
            'position': list(self.my_drone.coords),
            'velocity': list(self.my_drone.velocity),
            'residual_energy': self.my_drone.residual_energy,
            'cluster_epoch': self.cluster_epoch,
        }
        self._emit_control_packet(MACGControlPacket.CH_DECLARE, payload, dst_id=None)

    def _attempt_fallback_election(self):
        """CH fallback election (section 17): prevents permanent orphaning."""

        # Only compare against other UNCLUSTERED neighbors -- i.e. actual CH-candidacy competitors.
        # An already-clustered neighbor (CM/GW/CH) never re-enters this election itself, so comparing
        # against its frozen/stale stats can only ever block this node from ever self-electing without
        # anyone ever "winning" on its behalf -- the exact permanent-orphaning failure this fallback
        # exists to prevent. If there is nobody left to compete with (no neighbors at all, or every
        # neighbor already belongs to some cluster), self-elect immediately.
        neighbors = [(nid, entry) for nid, entry in self.neighbor_table.table.items()
                    if self.neighbor_table.is_item(nid) and entry[3] == ROLE_UNCLUSTERED]

        if not neighbors:
            # Case B: no competing neighbors -> become a (possibly singleton) CH
            self._become_ch()
            return True

        # Case A: self-elect only if strictly the strongest locally-visible candidate
        # (higher nomination count, then higher residual energy, then lower node id).
        #
        # Residual energy is bucketed to a coarse granularity before comparison: every drone drains
        # energy at essentially the same rate (flight power dominates communication cost), so raw
        # residual_energy values only ever differ by tiny, constantly-shifting amounts. Comparing
        # those raw floats -- especially "my" live value against a neighbor's slightly-stale
        # Hello-snapshot value -- means the energy term almost never ties exactly, which in turn
        # means the deterministic "lower node id" tie-break beneath it (the one thing guaranteed to
        # make this election converge) would almost never actually get a chance to apply. Bucketing
        # removes that noise while still letting a genuinely-depleted node lose the tie-break.
        best = (self.nomination_count, self._energy_tier(self.my_drone.residual_energy), self.my_drone.identifier)
        for nid, entry in neighbors:
            candidate = (entry[7], self._energy_tier(entry[2]), nid)  # (nomination_count, energy_tier, id)
            if (candidate[0] > best[0] or
                    (candidate[0] == best[0] and candidate[1] > best[1]) or
                    (candidate[0] == best[0] and candidate[1] == best[1] and candidate[2] < best[2])):
                return False

        self._become_ch()
        return True

    @staticmethod
    def _energy_tier(energy):
        """Coarse (0.1% of INITIAL_ENERGY) bucket used to compare residual energy for the CH
        fallback-election tie-break; see the comment in "_attempt_fallback_election" above."""

        if config.INITIAL_ENERGY <= 0:
            return 0
        return round(energy / config.INITIAL_ENERGY, 3)

    def _attempt_join_sequence(self):
        candidates = self._collect_visible_ch_candidates()
        ordered = sorted(candidates.items(),
                         key=lambda kv: (-kv[1]['similarity'], -kv[1]['residual_energy'], kv[0]))

        for ch_id, _info in ordered:
            self.diagnostics['join_attempts'] += 1
            self._send_join_request(ch_id)
            accepted = yield self.env.process(self._wait_join_accept(ch_id))
            if accepted:
                self.diagnostics['successful_joins'] += 1
                return True

        # no visible CH could be joined -> fall back to local CH election
        elected = self._attempt_fallback_election()
        return elected

    def _wait_join_accept(self, ch_id):
        self._pending_join_ch = ch_id
        self._join_accept_event = self.env.event()

        result = yield self._join_accept_event | self.env.timeout(config.MACG_JOIN_WINDOW)
        return self._join_accept_event in result

    def _collect_visible_ch_candidates(self):
        """
        Merge every currently-known CH candidate: CH_DECLARE/MAINTENANCE broadcasts observed so
        far ("visible_CHs", refreshed continuously since every CH re-broadcasts MAINTENANCE every
        MACG_MAINTENANCE_INTERVAL) plus any current one-hop neighbor whose last Hello reported it
        as a CH. All purely local/received information, no live-state inspection.
        """

        staleness = 3 * config.MACG_MAINTENANCE_INTERVAL
        now = self.env.now
        for ch_id in list(self.visible_CHs.keys()):
            if now - self.visible_CHs[ch_id]['time'] > staleness:
                del self.visible_CHs[ch_id]

        candidates = dict(self.visible_CHs)

        for nid, entry in self.neighbor_table.table.items():
            if self.neighbor_table.is_item(nid) and entry[3] == ROLE_CH:
                candidates[nid] = {
                    'position': entry[0],
                    'velocity': entry[1],
                    'residual_energy': entry[2],
                    'cluster_epoch': entry[6],
                    'similarity': self.neighbor_table.similarity_to(nid),
                    'time': entry[-1],
                }

        return candidates

    # ================================================================== #
    # active cluster: maintenance, member/CH timeout, re-association (sections 26-29)
    # ================================================================== #

    def _ch_active_loop(self):
        while True:
            for member_id in list(self.member_table.keys()):
                info = self.member_table[member_id]
                if info['responded']:
                    info['miss_count'] = 0
                else:
                    info['miss_count'] += 1
                info['responded'] = False

            to_remove = [mid for mid, info in self.member_table.items()
                        if info['miss_count'] >= config.MACG_MEMBER_MISS_LIMIT]
            for mid in to_remove:
                self._remove_member(mid)

            self._broadcast_maintenance()
            self._ch_self_scan_cross_links()

            jitter = self.rng.randint(1000, 2000)
            yield self.env.timeout(config.MACG_MAINTENANCE_INTERVAL + jitter)

    def _member_active_loop(self):
        self._ch_miss_count = 0
        self._maintenance_received_this_round = False
        poll_interval = config.MACG_MAINTENANCE_INTERVAL * 1.5  # tolerance margin around CH cadence

        while True:
            yield self.env.timeout(poll_interval)

            if self._maintenance_received_this_round:
                self._ch_miss_count = 0
            else:
                self._ch_miss_count += 1
            self._maintenance_received_this_round = False

            if self._ch_miss_count >= config.MACG_CH_MISS_LIMIT:
                logger.info('At time: %s (us) ---- UAV: %s lost its CH (%s), re-associating',
                            self.env.now, self.my_drone.identifier, self.cluster_head_id)

                self.diagnostics['re_associations'] += 1
                self.role = ROLE_UNCLUSTERED
                self.cluster_id = None
                self.cluster_head_id = None
                self.cluster_head_position = None
                self.cluster_head_velocity = None
                return

    def _remove_member(self, member_id):
        self.member_table.pop(member_id, None)
        links = self.member_external_links.pop(member_id, {})
        self.known_cluster_members.discard(member_id)
        self.diagnostics['member_removals'] += 1

        for neighbor_cluster_id in links.keys():
            self._recompute_gateway_entry(neighbor_cluster_id)

        self._broadcast_cluster_state()

    # ================================================================== #
    # gateway discovery & CH gateway table (sections 22-25)
    # ================================================================== #

    def refresh_gateway_role_and_report(self):
        """
        Called periodically (piggybacked on the existing Hello cadence in macg.py, so no separate
        high-frequency loop is introduced) by CM/GW nodes to: (1) update role CM<->GW based on
        current cross-cluster connectivity, and (2) immediately report brand-new neighboring
        clusters to the CH via GATEWAY_UPDATE instead of waiting for the next MAINTENANCE round.
        """

        if self.role not in (ROLE_CM, ROLE_GW):
            return

        self.neighbor_table.purge()
        groups = self.neighbor_table.cross_cluster_neighbors(self.cluster_id)

        if groups and self.role == ROLE_CM:
            self.role = ROLE_GW
        elif not groups and self.role == ROLE_GW:
            self.role = ROLE_CM

        current_cluster_ids = set(groups.keys())
        new_ones = current_cluster_ids - self._reported_clusters
        for neighbor_cluster_id in new_ones:
            best_id, best_similarity, best_entry = max(groups[neighbor_cluster_id], key=lambda t: t[1])
            payload = {
                'member_id': self.my_drone.identifier,
                'neighbor_cluster_id': neighbor_cluster_id,
                'external_neighbor_id': best_id,
                'external_neighbor_position': best_entry[0],
                'similarity': best_similarity,
                'count': len(groups[neighbor_cluster_id]),
            }
            self._emit_control_packet(MACGControlPacket.GATEWAY_UPDATE, payload, dst_id=self.cluster_head_id)

        self._reported_clusters = current_cluster_ids

    def _ch_self_scan_cross_links(self):
        """A CH may itself have direct cross-cluster neighbors without changing ROLE_CH (section 22)"""

        self.neighbor_table.purge()
        groups = self.neighbor_table.cross_cluster_neighbors(self.cluster_id)

        old_links = self.member_external_links.get(self.my_drone.identifier, {})
        new_links = {}
        for neighbor_cluster_id, links in groups.items():
            best_id, best_similarity, best_entry = max(links, key=lambda t: t[1])
            new_links[neighbor_cluster_id] = {
                'external_neighbor_id': best_id,
                'external_neighbor_position': best_entry[0],
                'similarity': best_similarity,
                'count': len(links),
            }
        self.member_external_links[self.my_drone.identifier] = new_links

        affected = set(old_links.keys()) | set(new_links.keys())
        for neighbor_cluster_id in affected:
            self._recompute_gateway_entry(neighbor_cluster_id)

    def _recompute_gateway_entry(self, neighbor_cluster_id):
        """
        Gateway selection rule (section 25): highest number of valid links into the neighboring
        cluster, then highest cross-link mobility similarity, then highest residual energy, then
        lowest node id. Only ever scans "member_external_links", which is built exclusively from
        this CH's own members' reports (plus the CH's own self-scan) -- fully local state.
        """

        best_member = None
        best_key = None

        for member_id, links in self.member_external_links.items():
            if neighbor_cluster_id not in links:
                continue
            if member_id != self.my_drone.identifier and member_id not in self.member_table:
                continue  # stale entry for a member that has since been removed

            link = links[neighbor_cluster_id]
            energy = (self.my_drone.residual_energy if member_id == self.my_drone.identifier
                     else self.member_table[member_id]['residual_energy'])
            key = (-link['count'], -link['similarity'], -energy, member_id)

            if best_key is None or key < best_key:
                best_key = key
                best_member = (member_id, link, energy)

        if best_member is None:
            self.gateway_table.pop(neighbor_cluster_id, None)
            return

        member_id, link, energy = best_member
        previous = self.gateway_table.get(neighbor_cluster_id)
        if previous is None or previous.get('local_gateway_id') != member_id:
            self.diagnostics['gateway_changes'] += 1

        self.gateway_table[neighbor_cluster_id] = {
            'local_gateway_id': member_id,
            'external_neighbor_id': link['external_neighbor_id'],
            'external_neighbor_position': link['external_neighbor_position'],
            'cross_link_count': link['count'],
            'cross_link_similarity': link['similarity'],
            'gateway_energy': energy,
            'last_update_time': self.env.now,
        }

    def purge_stale_gateways(self):
        threshold = 3 * config.MACG_MAINTENANCE_INTERVAL
        now = self.env.now
        for neighbor_cluster_id in list(self.gateway_table.keys()):
            if now - self.gateway_table[neighbor_cluster_id]['last_update_time'] > threshold:
                del self.gateway_table[neighbor_cluster_id]

    def select_gateway_for_destination(self, destination_position, avoid_cluster_id=None, visited_clusters=None):
        """
        CH inter-cluster decision (section 37): pick the neighboring-cluster gateway whose
        advertised external neighbor is geographically closest to the final destination.

        :return: (neighbor_cluster_id, gateway_entry dict) or None if no usable gateway exists
        """

        self.purge_stale_gateways()
        if not self.gateway_table:
            return None

        visited_clusters = visited_clusters or []
        items = list(self.gateway_table.items())

        # avoid immediately returning to the previous cluster when another option exists
        preferred = [item for item in items
                    if item[0] != avoid_cluster_id and item[0] not in visited_clusters]
        pool = preferred if preferred else items

        best = None
        best_key = None
        for neighbor_cluster_id, entry in pool:
            distance = euclidean_distance_3d(entry['external_neighbor_position'], destination_position)
            key = (distance, -entry['cross_link_similarity'], -entry['gateway_energy'], entry['local_gateway_id'])
            if best_key is None or key < best_key:
                best_key = key
                best = (neighbor_cluster_id, entry)

        return best

    # ================================================================== #
    # control packet handlers
    # ================================================================== #

    def handle_control_packet(self, packet, src_drone_id):
        message_type = packet.message_type

        if message_type == MACGControlPacket.NOMINATION:
            self._on_nomination(packet, src_drone_id)
        elif message_type == MACGControlPacket.CH_DECLARE:
            self._on_ch_declare(packet, src_drone_id)
        elif message_type == MACGControlPacket.JOIN_REQUEST:
            self._on_join_request(packet, src_drone_id)
        elif message_type == MACGControlPacket.JOIN_ACCEPT:
            self._on_join_accept(packet, src_drone_id)
        elif message_type == MACGControlPacket.CLUSTER_STATE:
            self._on_cluster_state(packet, src_drone_id)
        elif message_type == MACGControlPacket.MAINTENANCE:
            self._on_maintenance(packet, src_drone_id)
        elif message_type == MACGControlPacket.MAINT_RESPONSE:
            self._on_maint_response(packet, src_drone_id)
        elif message_type == MACGControlPacket.GATEWAY_UPDATE:
            self._on_gateway_update(packet, src_drone_id)
        else:
            logger.warning('Unknown MACG control message type: %s', message_type)

    def _on_nomination(self, packet, src_drone_id):
        if packet.dst_id != self.my_drone.identifier:
            return
        if not self._collecting_nominations or self.role != ROLE_UNCLUSTERED:
            return
        if packet.payload.get('target_epoch') != self.cluster_epoch:
            return  # stale-epoch nomination (section 15)
        if src_drone_id in self.nominators:
            return  # duplicate nomination

        self.nominators.add(src_drone_id)
        self.nomination_count += 1

    def _on_ch_declare(self, packet, src_drone_id):
        payload = packet.payload
        ch_id = payload['ch_id']
        similarity = self.neighbor_table.compute_similarity(self.my_drone.coords, self.my_drone.velocity,
                                                             payload['position'], payload['velocity'])
        self.visible_CHs[ch_id] = {
            'position': payload['position'],
            'velocity': payload['velocity'],
            'residual_energy': payload['residual_energy'],
            'cluster_epoch': payload['cluster_epoch'],
            'similarity': similarity,
            'time': self.env.now,
        }

    def _on_join_request(self, packet, src_drone_id):
        if packet.dst_id != self.my_drone.identifier or self.role != ROLE_CH:
            return

        payload = packet.payload
        member_id = payload['member_id']
        self.member_table[member_id] = {
            'last_response_time': self.env.now,
            'position': payload['position'],
            'velocity': payload['velocity'],
            'residual_energy': payload['residual_energy'],
            'miss_count': 0,
            'responded': True,
        }
        self.known_cluster_members.add(member_id)

        accept_payload = {
            'cluster_id': self.cluster_id,
            'cluster_head_id': self.cluster_head_id,
            'cluster_epoch': self.cluster_epoch,
            'ch_position': list(self.my_drone.coords),
            'ch_velocity': list(self.my_drone.velocity),
        }
        self._emit_control_packet(MACGControlPacket.JOIN_ACCEPT, accept_payload, dst_id=member_id)
        self._broadcast_cluster_state()

    def _on_join_accept(self, packet, src_drone_id):
        if packet.dst_id != self.my_drone.identifier:
            return
        if self._join_accept_event is None or self._join_accept_event.triggered:
            return
        if self._pending_join_ch != src_drone_id:
            return

        payload = packet.payload
        self.role = ROLE_CM
        self.cluster_id = payload['cluster_id']
        self.cluster_head_id = payload['cluster_head_id']
        self.cluster_epoch = payload['cluster_epoch']
        self.cluster_head_position = payload['ch_position']
        self.cluster_head_velocity = payload['ch_velocity']
        self.known_cluster_members = set()
        self._reported_clusters = set()

        self._join_accept_event.succeed()

    def _on_cluster_state(self, packet, src_drone_id):
        if self.role in (ROLE_CM, ROLE_GW) and self.cluster_head_id == src_drone_id:
            self.known_cluster_members = set(packet.payload.get('member_ids', []))
            self.known_cluster_members.add(src_drone_id)

    def _on_maintenance(self, packet, src_drone_id):
        payload = packet.payload
        ch_id = payload['ch_id']

        similarity = self.neighbor_table.compute_similarity(self.my_drone.coords, self.my_drone.velocity,
                                                             payload['ch_position'], payload['ch_velocity'])
        self.visible_CHs[ch_id] = {
            'position': payload['ch_position'],
            'velocity': payload['ch_velocity'],
            'residual_energy': self.visible_CHs.get(ch_id, {}).get('residual_energy', 0.0),
            'cluster_epoch': payload['cluster_epoch'],
            'similarity': similarity,
            'time': self.env.now,
        }

        if (self.role in (ROLE_CM, ROLE_GW) and self.cluster_head_id == ch_id
                and self.cluster_id == payload['cluster_id']):
            self._maintenance_received_this_round = True
            self.cluster_head_position = payload['ch_position']
            self.cluster_head_velocity = payload['ch_velocity']
            self._send_maint_response(ch_id)

    def _on_maint_response(self, packet, src_drone_id):
        if packet.dst_id != self.my_drone.identifier or self.role != ROLE_CH:
            return

        payload = packet.payload
        member_id = payload['member_id']
        if member_id not in self.member_table:
            return  # stray response from a member that has already been removed

        info = self.member_table[member_id]
        info['position'] = payload['position']
        info['velocity'] = payload['velocity']
        info['residual_energy'] = payload['residual_energy']
        info['last_response_time'] = self.env.now
        info['responded'] = True

        old_links = self.member_external_links.get(member_id, {})
        new_links = {link['neighbor_cluster_id']: {
                        'external_neighbor_id': link['external_neighbor_id'],
                        'external_neighbor_position': link['external_neighbor_position'],
                        'similarity': link['similarity'],
                        'count': link['count'],
                    } for link in payload['external_links']}
        self.member_external_links[member_id] = new_links

        affected = set(old_links.keys()) | set(new_links.keys())
        for neighbor_cluster_id in affected:
            self._recompute_gateway_entry(neighbor_cluster_id)

    def _on_gateway_update(self, packet, src_drone_id):
        if packet.dst_id != self.my_drone.identifier or self.role != ROLE_CH:
            return

        payload = packet.payload
        member_id = payload['member_id']
        if member_id != self.my_drone.identifier and member_id not in self.member_table:
            return

        neighbor_cluster_id = payload['neighbor_cluster_id']
        self.member_external_links.setdefault(member_id, {})[neighbor_cluster_id] = {
            'external_neighbor_id': payload['external_neighbor_id'],
            'external_neighbor_position': payload['external_neighbor_position'],
            'similarity': payload['similarity'],
            'count': payload['count'],
        }
        self._recompute_gateway_entry(neighbor_cluster_id)

    # ================================================================== #
    # outgoing control packet helpers
    # ================================================================== #

    def _send_nomination(self, target_id):
        payload = {
            'target_id': target_id,
            'target_epoch': self.neighbor_table.get_cluster_epoch(target_id),
            'sender_epoch': self.cluster_epoch,
            'residual_energy': self.my_drone.residual_energy,
        }
        self._emit_control_packet(MACGControlPacket.NOMINATION, payload, dst_id=target_id)

    def _send_join_request(self, ch_id):
        payload = {
            'member_id': self.my_drone.identifier,
            'position': list(self.my_drone.coords),
            'velocity': list(self.my_drone.velocity),
            'residual_energy': self.my_drone.residual_energy,
            'cluster_epoch': self.cluster_epoch,
        }
        self._emit_control_packet(MACGControlPacket.JOIN_REQUEST, payload, dst_id=ch_id)

    def _send_maint_response(self, ch_id):
        self.neighbor_table.purge()
        groups = self.neighbor_table.cross_cluster_neighbors(self.cluster_id)

        external_links = []
        for neighbor_cluster_id, links in groups.items():
            best_id, best_similarity, best_entry = max(links, key=lambda t: t[1])
            external_links.append({
                'neighbor_cluster_id': neighbor_cluster_id,
                'external_neighbor_id': best_id,
                'external_neighbor_position': best_entry[0],
                'similarity': best_similarity,
                'count': len(links),
            })

        if groups and self.role == ROLE_CM:
            self.role = ROLE_GW
        elif not groups and self.role == ROLE_GW:
            self.role = ROLE_CM

        payload = {
            'member_id': self.my_drone.identifier,
            'position': list(self.my_drone.coords),
            'velocity': list(self.my_drone.velocity),
            'residual_energy': self.my_drone.residual_energy,
            'external_links': external_links,
        }
        self._emit_control_packet(MACGControlPacket.MAINT_RESPONSE, payload, dst_id=ch_id)

    def _broadcast_maintenance(self):
        payload = {
            'ch_id': self.my_drone.identifier,
            'cluster_id': self.cluster_id,
            'cluster_epoch': self.cluster_epoch,
            'ch_position': list(self.my_drone.coords),
            'ch_velocity': list(self.my_drone.velocity),
            'timestamp': self.env.now,
        }
        self._emit_control_packet(MACGControlPacket.MAINTENANCE, payload, dst_id=None)

    def _broadcast_cluster_state(self):
        payload = {
            'cluster_id': self.cluster_id,
            'cluster_head_id': self.cluster_head_id,
            'cluster_epoch': self.cluster_epoch,
            'member_ids': list(self.member_table.keys()),
        }
        self._emit_control_packet(MACGControlPacket.CLUSTER_STATE, payload, dst_id=None)

    def _emit_control_packet(self, message_type, payload, dst_id=None):
        config.GL_ID_MACG_CONTROL_PACKET += 1

        channel_id = self.my_drone.channel_assigner.channel_assign()

        packet = MACGControlPacket(
            src_drone=self.my_drone,
            dst_id=dst_id,
            creation_time=self.env.now,
            id_packet=config.GL_ID_MACG_CONTROL_PACKET,
            packet_length=config.MACG_CONTROL_PACKET_LENGTH,
            message_type=message_type,
            payload=payload,
            simulator=self.simulator,
            channel_id=channel_id,
        )
        packet.transmission_mode = 1  # broadcast, following this repository's control-packet convention

        self.simulator.metrics.control_packet_num += 1
        self.my_drone.transmitting_queue.put(packet)
        return packet


def collect_swarm_diagnostics(simulator):
    """
    OPTIONAL debug/reporting-only utility that aggregates network-wide MACG diagnostics (active
    cluster count, average/maximum cluster size, CH/GW/CM/unclustered counts) across every drone
    running MACG.

    This function must NEVER be called from routing/clustering decision logic. MACG's actual
    protocol behavior (everything above) only ever uses local state, received control packets and
    the local neighbor table. This helper exists purely so an end-of-simulation report can print a
    network-wide summary, exactly like "simulator.metrics.print_metrics()" already does for the
    routing-agnostic metrics -- it is not part of, and is never consulted by, any routing decision.
    """

    from routing.macg.macg import MACG  # local import: avoids a module import cycle

    roles = {ROLE_UNCLUSTERED: 0, ROLE_CH: 0, ROLE_GW: 0, ROLE_CM: 0}
    cluster_sizes = {}

    for drone in simulator.drones:
        if not isinstance(drone.routing_protocol, MACG):
            continue

        cluster_manager = drone.routing_protocol.cluster_manager
        roles[cluster_manager.role] = roles.get(cluster_manager.role, 0) + 1

        if cluster_manager.role == ROLE_CH:
            cluster_sizes[cluster_manager.cluster_id] = len(cluster_manager.member_table) + 1

    active_clusters = len(cluster_sizes)
    sizes = list(cluster_sizes.values())

    return {
        'active_cluster_count': active_clusters,
        'average_cluster_size': (sum(sizes) / active_clusters) if active_clusters else 0.0,
        'maximum_cluster_size': max(sizes) if sizes else 0,
        'ch_count': roles[ROLE_CH],
        'gw_count': roles[ROLE_GW],
        'cm_count': roles[ROLE_CM],
        'unclustered_count': roles[ROLE_UNCLUSTERED],
    }
