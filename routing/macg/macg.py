import copy
import random
from simulator.log import logger
from entities.packet import DataPacket, AckPacket
from topology.virtual_force.vf_packet import VfPacket
from routing.macg.macg_neighbor_table import MACGNeighborTable
from routing.macg.macg_packet import MACGHelloPacket, MACGControlPacket
from routing.macg.macg_cluster_manager import MACGClusterManager, ROLE_UNCLUSTERED, ROLE_CH
from utils import config


class MACG:
    """
    Main procedure of MACG (Mobility-Aware Clustered Greedy Routing)

    MACG is a GMDC-inspired hierarchical routing protocol: it organizes the swarm into
    mobility-stable clusters (Cluster Heads + members + inter-cluster gateways, all owned by
    "MACGClusterManager") and keeps the actual data-plane forwarding rule ordinary, deterministic
    Greedy (owned by "MACGNeighborTable.best_neighbor_towards"). Mobility similarity is used only
    to organize the swarm into clusters -- it never enters the next-hop distance comparison itself.

    This class owns the data-routing layer: DataPacket next-hop selection (including the
    hierarchical LOCAL / TO_CH / TO_GATEWAY forwarding stages and their mandatory flat-Greedy
    fallbacks), DataPacket reception, ordinary DataPacket ACK handling and waiting-list behavior
    (all identical in spirit to the existing Greedy protocol -- no second data-reliability
    mechanism is introduced), and MACG Hello broadcast/reception. The clustering state machine
    itself (nomination, CH election, joining, gateway discovery, maintenance, re-association)
    lives in "MACGClusterManager"; this class only reads its public state and forwards received
    control packets to it.

    Attributes:
        simulator: the simulation platform that contains everything
        my_drone: the drone that installed MACG
        rng_routing: a Random class based on which we can call the function that generates the random number
        hello_interval: interval of sending hello packet
        neighbor_table: one-hop neighbor table of MACG (position/velocity/energy/role/cluster state)
        cluster_manager: owns clustering state and clustering control logic

    Author: MACG implementation
    """

    def __init__(self, simulator, my_drone):
        self.simulator = simulator
        self.my_drone = my_drone
        self.env = simulator.env
        self.rng_routing = random.Random(self.my_drone.identifier + self.my_drone.simulator.seed + 10)
        self.hello_interval = config.MACG_HELLO_INTERVAL
        self.check_interval = 0.6 * 1e6

        self.neighbor_table = MACGNeighborTable(self.simulator.env, my_drone)
        self.cluster_manager = MACGClusterManager(self.simulator, my_drone, self.neighbor_table)

        self.simulator.env.process(self.broadcast_hello_packet_periodically())
        self.simulator.env.process(self.check_waiting_list())
        self.cluster_manager.start()

    # ================================================================== #
    # Hello (phase 1 / section 9)
    # ================================================================== #

    def broadcast_hello_packet(self, my_drone):
        config.GL_ID_HELLO_PACKET += 1

        # channel assignment
        channel_id = self.my_drone.channel_assigner.channel_assign()

        hello_pkd = MACGHelloPacket(src_drone=my_drone,
                                    creation_time=self.simulator.env.now,
                                    id_hello_packet=config.GL_ID_HELLO_PACKET,
                                    hello_packet_length=config.HELLO_PACKET_LENGTH,
                                    simulator=self.simulator,
                                    channel_id=channel_id,
                                    cluster_manager=self.cluster_manager)
        hello_pkd.transmission_mode = 1

        logger.info('At time: %s (us) ---- UAV: %s has a MACG hello packet to broadcast',
                    self.simulator.env.now, self.my_drone.identifier)

        self.simulator.metrics.control_packet_num += 1
        self.my_drone.transmitting_queue.put(hello_pkd)

    def broadcast_hello_packet_periodically(self):
        while True:
            self.broadcast_hello_packet(self.my_drone)

            # piggyback the gateway-role refresh + prompt GATEWAY_UPDATE reporting on the existing
            # Hello cadence instead of running a separate high-frequency loop (section 23)
            self.cluster_manager.refresh_gateway_role_and_report()

            jitter = self.rng_routing.randint(1000, 2000)  # delay jitter
            yield self.simulator.env.timeout(self.hello_interval + jitter)

    # ================================================================== #
    # DataPacket next-hop selection (phases 8-14, sections 30-43)
    # ================================================================== #

    def next_hop_selection(self, packet):
        """
        Select the next hop according to the routing protocol

        Parameters:
            packet: the data packet that needs to be sent

        Returns:
            next hop drone id
        """

        has_route = True
        enquire = False  # "True" when reactive protocol is adopted

        next_hop_id = self._compute_next_hop(packet)

        if next_hop_id == self.my_drone.identifier:
            has_route = False  # no available next hop
        else:
            packet.next_hop_id = next_hop_id

        return has_route, packet, enquire

    @staticmethod
    def _ensure_macg_state(packet):
        if not hasattr(packet, 'macg_stage'):
            packet.macg_stage = 'LOCAL'
            packet.macg_target_id = None
            packet.macg_target_position = None
            packet.macg_selected_neighbor_cluster = None
            packet.macg_selected_external_neighbor = None
            packet.macg_last_cluster = None
            packet.macg_visited_clusters = []

    def _compute_next_hop(self, packet):
        """
        Deterministic hierarchical-Greedy next-hop computation, shared by "next_hop_selection()"
        and "check_waiting_list()". Mutates the packet's "macg_*" metadata as needed and returns
        the chosen next hop id (or "my_drone.identifier" if no next hop is currently available).
        """

        self.neighbor_table.purge()
        self._ensure_macg_state(packet)

        dst_drone = packet.dst_drone
        dst_id = dst_drone.identifier
        cluster_manager = self.cluster_manager

        # --- direct one-hop neighbor fast path, always checked first (section 33) --- #
        if self.neighbor_table.is_item(dst_id):
            packet.macg_stage = 'LOCAL'
            packet.macg_target_id = None
            packet.macg_target_position = None
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return dst_id

        role = cluster_manager.role

        # --- unclustered: flat original-style Greedy (section 34) --- #
        if role == ROLE_UNCLUSTERED:
            return self._flat_greedy(packet, dst_drone.coords)

        # --- CH: always re-derives the local/inter-cluster decision itself (section 41) --- #
        if role == ROLE_CH:
            return self._ch_route(packet, dst_drone)

        # --- CM / GW --- #
        # if already mid-transit toward a previously-selected gateway, keep heading there instead
        # of re-deriving "member-to-CH" from scratch (avoids oscillation)
        if packet.macg_stage == 'TO_GATEWAY' and packet.macg_target_id is not None:
            return self._continue_to_gateway(packet)

        if dst_id in cluster_manager.known_cluster_members or dst_id == cluster_manager.cluster_head_id:
            return self._same_cluster_route(packet, dst_drone.coords)

        return self._member_to_ch_route(packet, dst_drone)

    # ------------------------------------------------------------------ #
    # forwarding stages
    # ------------------------------------------------------------------ #

    def _flat_greedy(self, packet, target_position):
        packet.macg_stage = 'LOCAL'
        packet.macg_target_id = None
        packet.macg_target_position = None

        next_hop = self.neighbor_table.best_neighbor_towards(target_position)
        self.cluster_manager.diagnostics['flat_greedy_fallback_count'] += 1
        return next_hop

    def _same_cluster_route(self, packet, target_position):
        """Section 35: prefer same-cluster neighbors, flat-Greedy fallback if none make progress"""

        packet.macg_stage = 'LOCAL'
        packet.macg_target_id = None
        packet.macg_target_position = None

        cluster_manager = self.cluster_manager
        next_hop = self.neighbor_table.best_neighbor_towards(target_position, allowed_cluster_id=cluster_manager.cluster_id)

        if next_hop != self.my_drone.identifier:
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return next_hop

        return self._flat_greedy(packet, target_position)

    def _member_to_ch_route(self, packet, dst_drone):
        """Section 36: Greedy target is the own CH, not the final destination"""

        cluster_manager = self.cluster_manager

        if cluster_manager.cluster_head_position is None:
            return self._flat_greedy(packet, dst_drone.coords)

        packet.macg_stage = 'TO_CH'
        packet.macg_target_id = cluster_manager.cluster_head_id
        packet.macg_target_position = cluster_manager.cluster_head_position

        if self.neighbor_table.is_item(cluster_manager.cluster_head_id):
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return cluster_manager.cluster_head_id

        next_hop = self.neighbor_table.best_neighbor_towards(cluster_manager.cluster_head_position,
                                                              allowed_cluster_id=cluster_manager.cluster_id)
        if next_hop != self.my_drone.identifier:
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return next_hop

        # cannot Greedy-route to CH -> mandatory fallback (section 43)
        return self._flat_greedy(packet, dst_drone.coords)

    def _ch_route(self, packet, dst_drone):
        """Sections 37, 39, 41: CH local/inter-cluster decision"""

        cluster_manager = self.cluster_manager
        dst_id = dst_drone.identifier

        if cluster_manager.is_member(dst_id):
            return self._same_cluster_route(packet, dst_drone.coords)

        selection = cluster_manager.select_gateway_for_destination(
            dst_drone.coords,
            avoid_cluster_id=packet.macg_last_cluster,
            visited_clusters=packet.macg_visited_clusters)

        if selection is None:
            # CH has no valid gateway -> mandatory fallback (section 43)
            packet.macg_stage = 'LOCAL'
            packet.macg_target_id = None
            packet.macg_target_position = None
            return self._flat_greedy(packet, dst_drone.coords)

        neighbor_cluster_id, entry = selection
        gateway_id = entry['local_gateway_id']

        packet.macg_stage = 'TO_GATEWAY'
        packet.macg_target_id = gateway_id
        packet.macg_selected_neighbor_cluster = neighbor_cluster_id
        packet.macg_selected_external_neighbor = entry['external_neighbor_id']

        if gateway_id == self.my_drone.identifier:
            # the CH itself has the best cross-cluster link (section 22) -> cross right here
            return self._cross_cluster_transfer(packet, entry['external_neighbor_id'], neighbor_cluster_id)

        gateway_position = (cluster_manager.member_table[gateway_id]['position']
                            if gateway_id in cluster_manager.member_table
                            else entry['external_neighbor_position'])
        packet.macg_target_position = gateway_position

        if self.neighbor_table.is_item(gateway_id):
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return gateway_id

        next_hop = self.neighbor_table.best_neighbor_towards(gateway_position, allowed_cluster_id=cluster_manager.cluster_id)
        if next_hop != self.my_drone.identifier:
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return next_hop

        # cannot Greedy-route to the selected gateway -> mandatory fallback (section 43)
        packet.macg_stage = 'LOCAL'
        packet.macg_target_id = None
        packet.macg_target_position = None
        return self._flat_greedy(packet, dst_drone.coords)

    def _continue_to_gateway(self, packet):
        """Section 39: intra-cluster Greedy toward a previously-selected gateway"""

        cluster_manager = self.cluster_manager
        gateway_id = packet.macg_target_id

        if gateway_id == self.my_drone.identifier:
            return self._cross_cluster_transfer(packet, packet.macg_selected_external_neighbor,
                                                packet.macg_selected_neighbor_cluster)

        if self.neighbor_table.is_item(gateway_id):
            cluster_manager.diagnostics['hierarchical_forward_count'] += 1
            return gateway_id

        target_position = packet.macg_target_position
        if target_position is not None:
            next_hop = self.neighbor_table.best_neighbor_towards(target_position, allowed_cluster_id=cluster_manager.cluster_id)
            if next_hop != self.my_drone.identifier:
                cluster_manager.diagnostics['hierarchical_forward_count'] += 1
                return next_hop

        # lost progress toward the gateway mid-transit -> clear hierarchy state, flat-Greedy fallback
        packet.macg_stage = 'LOCAL'
        packet.macg_target_id = None
        packet.macg_target_position = None
        packet.macg_selected_neighbor_cluster = None
        packet.macg_selected_external_neighbor = None
        return self._flat_greedy(packet, packet.dst_drone.coords)

    def _cross_cluster_transfer(self, packet, external_neighbor_id, expected_cluster_id):
        """Section 40: validate + forward directly across the cluster boundary"""

        cluster_manager = self.cluster_manager
        own_cluster_id = cluster_manager.cluster_id

        valid = (external_neighbor_id is not None
                and self.neighbor_table.is_item(external_neighbor_id)
                and self.neighbor_table.get_cluster_id(external_neighbor_id) not in (None, own_cluster_id))

        if not valid:
            external_neighbor_id = self._recompute_external_neighbor(expected_cluster_id, own_cluster_id)

        if external_neighbor_id is None:
            # external neighbor disappeared and none remains -> clear hierarchy, flat-Greedy fallback
            packet.macg_stage = 'LOCAL'
            packet.macg_target_id = None
            packet.macg_target_position = None
            packet.macg_selected_neighbor_cluster = None
            packet.macg_selected_external_neighbor = None
            return self._flat_greedy(packet, packet.dst_drone.coords)

        packet.macg_last_cluster = own_cluster_id
        visited = packet.macg_visited_clusters
        if own_cluster_id not in visited:
            visited.append(own_cluster_id)
        while len(visited) > config.MACG_VISITED_CLUSTER_LIMIT:
            del visited[0]
        packet.macg_visited_clusters = visited

        packet.macg_stage = 'TO_CH'
        packet.macg_target_id = None
        packet.macg_target_position = None
        packet.macg_selected_neighbor_cluster = None
        packet.macg_selected_external_neighbor = None

        cluster_manager.diagnostics['hierarchical_forward_count'] += 1
        return external_neighbor_id

    def _recompute_external_neighbor(self, expected_cluster_id, own_cluster_id):
        self.neighbor_table.purge()
        if expected_cluster_id is None:
            return None

        groups = self.neighbor_table.cross_cluster_neighbors(own_cluster_id)
        candidates = groups.get(expected_cluster_id)
        if not candidates:
            return None

        best_id, _similarity, _entry = max(candidates, key=lambda t: t[1])
        return best_id

    # ================================================================== #
    # packet reception (unchanged ACK/waiting-list behavior, section 44)
    # ================================================================== #

    def packet_reception(self, packet, src_drone_id):
        """
        Packet reception at network layer

        since different routing protocols have their own corresponding packets, it is necessary to add this packet
        reception function in the network layer

        Parameters:
            packet: the received packet
            src_drone_id: previous hop
        """

        current_time = self.simulator.env.now

        if isinstance(packet, MACGHelloPacket):
            self.neighbor_table.add_item(packet, current_time)  # update the neighbor table
            self.neighbor_table.print_item(self.my_drone)

        elif isinstance(packet, MACGControlPacket):
            self.cluster_manager.handle_control_packet(packet, src_drone_id)

        elif isinstance(packet, DataPacket):
            packet_copy = copy.copy(packet)

            if packet_copy.dst_drone.identifier == self.my_drone.identifier:
                if packet_copy.packet_id not in self.simulator.metrics.datapacket_arrived:
                    self.simulator.metrics.calculate_metrics(packet_copy)

                    logger.info('At time: %s (us) ---- Data packet: %s is received by destination UAV: %s',
                                self.simulator.env.now, packet_copy.packet_id, self.my_drone.identifier)

                # reply ACK
                config.GL_ID_ACK_PACKET += 1
                src_drone = self.simulator.drones[src_drone_id]  # previous drone

                # NOTE: The pair of transceivers for a particular link are tuned to the same channel for transmission
                # in either direction (i.e., there is no directionality in channel assignment).
                ack_packet = AckPacket(src_drone=self.my_drone,
                                       dst_drone=src_drone,
                                       ack_packet_id=config.GL_ID_ACK_PACKET,
                                       ack_packet_length=config.ACK_PACKET_LENGTH,
                                       ack_packet=packet_copy,
                                       simulator=self.simulator,
                                       channel_id=packet_copy.channel_id)

                yield self.simulator.env.process(self.my_drone.mac_protocol.send_ack(ack_packet, src_drone_id))
            else:
                if self.my_drone.transmitting_queue.qsize() < self.my_drone.max_queue_size:  # have enough capacity
                    logger.info('At time: %s (us) ---- Data packet: %s is received by next hop UAV: %s',
                                self.simulator.env.now, packet_copy.packet_id, self.my_drone.identifier)

                    self.my_drone.transmitting_queue.put(packet_copy)  # add this packet into my own queue

                    config.GL_ID_ACK_PACKET += 1
                    src_drone = self.simulator.drones[src_drone_id]  # previous drone
                    ack_packet = AckPacket(src_drone=self.my_drone,
                                           dst_drone=src_drone,
                                           ack_packet_id=config.GL_ID_ACK_PACKET,
                                           ack_packet_length=config.ACK_PACKET_LENGTH,
                                           ack_packet=packet_copy,
                                           simulator=self.simulator,
                                           channel_id=packet_copy.channel_id)

                    yield self.simulator.env.process(self.my_drone.mac_protocol.send_ack(ack_packet, src_drone_id))
                else:  # the queue is full, discard this packet and no ACK reply
                    pass

        elif isinstance(packet, AckPacket):
            data_packet_acked = packet.ack_packet

            self.simulator.metrics.mac_delay.append(
                (self.simulator.env.now - data_packet_acked.first_attempt_time) / 1e3)

            self.my_drone.remove_from_queue(data_packet_acked)

            self.my_drone.mac_protocol.unblock_wait_ack(data_packet_acked.packet_id, src_drone_id)

        elif isinstance(packet, VfPacket):
            logger.info('At time: %s (us) ---- UAV: %s receives the vf hello msg from UAV: %s, pkd id is: %s',
                        self.simulator.env.now, self.my_drone.identifier, src_drone_id, packet.packet_id)

            # update the neighbor table
            self.my_drone.motion_controller.neighbor_table.add_neighbor(packet, current_time)

            if packet.msg_type == 'hello':
                config.GL_ID_VF_PACKET += 1

                # channel assignment
                channel_id = self.my_drone.channel_assigner.channel_assign()

                ack_packet = VfPacket(src_drone=self.my_drone,
                                      creation_time=self.simulator.env.now,
                                      id_hello_packet=config.GL_ID_VF_PACKET,
                                      hello_packet_length=config.HELLO_PACKET_LENGTH,
                                      simulator=self.simulator,
                                      channel_id=channel_id)
                ack_packet.msg_type = 'ack'

                self.my_drone.transmitting_queue.put(ack_packet)
            else:
                pass

    def check_waiting_list(self):
        while True:
            if not self.my_drone.sleep:
                yield self.simulator.env.timeout(self.check_interval)
                for waiting_pkd in list(self.my_drone.waiting_list):
                    if self.simulator.env.now > waiting_pkd.creation_time + waiting_pkd.deadline:
                        self.my_drone.waiting_list.remove(waiting_pkd)
                    else:
                        next_hop_id = self._compute_next_hop(waiting_pkd)
                        if next_hop_id != self.my_drone.identifier:
                            waiting_pkd.next_hop_id = next_hop_id
                            self.my_drone.transmitting_queue.put(waiting_pkd)
                            self.my_drone.waiting_list.remove(waiting_pkd)
                        else:
                            pass
            else:
                break

    def penalize(self, packet):
        pass
