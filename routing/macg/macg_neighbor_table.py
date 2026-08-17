from simulator.log import logger
from utils import config
from utils.util_function import euclidean_distance_3d
from phy.large_scale_fading import maximum_communication_range
from routing.base.base_table import BaseTable


class MACGNeighborTable(BaseTable):
    """
    One-hop neighbor table of MACG routing.

    Type of the neighbor table: dictionary
    The structure of the neighbor table is:
        {drone_id: [position, velocity, residual_energy, role, cluster_id, cluster_head_id,
                     cluster_epoch, nomination_count, mobility_similarity, updated_time], ...}

    "updated_time" MUST stay the last element of each entry, since "BaseTable.get_updated_time()"
    relies on "self.table[drone_id][-1]" to retrieve it.

    All information stored here is learned exclusively from received MACG Hello packets (the only
    exception is "mobility_similarity", which is a value this drone derives locally from its own
    live state plus the neighbor's last-known snapshot -- never from another drone's live state).
    Stale entries (no Hello heard for "entry_life_time") are purged the same way every other
    routing protocol in this repository purges its neighbor table.

    Author: MACG implementation
    """

    def __init__(self, env, my_drone):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone

    # ------------------------------------------------------------------ #
    # storage
    # ------------------------------------------------------------------ #

    def add_item(self, hello_packet, cur_time):
        """
        Update the neighbor table according to a received MACGHelloPacket
        :param hello_packet: the received MACGHelloPacket
        :param cur_time: the moment when the packet is received
        :return: None
        """

        drone_id = hello_packet.src_drone.identifier
        similarity = self.compute_similarity(self.my_drone.coords, self.my_drone.velocity,
                                              hello_packet.cur_position, hello_packet.cur_velocity)

        self.table[drone_id] = [
            hello_packet.cur_position,
            hello_packet.cur_velocity,
            hello_packet.residual_energy,
            hello_packet.role,
            hello_packet.cluster_id,
            hello_packet.cluster_head_id,
            hello_packet.cluster_epoch,
            hello_packet.nomination_count,
            similarity,
            cur_time,
        ]

    def print_item(self, my_drone):
        logger.info('|----------MACG Neighbor Table of: %s ----------|', my_drone.identifier)
        for key in self.table:
            entry = self.table[key]
            logger.info('Neighbor: %s, position: %s, role: %s, cluster_id: %s, ch_id: %s, '
                        'epoch: %s, similarity: %s, updated time: %s',
                        key, entry[0], entry[3], entry[4], entry[5], entry[6], entry[8], entry[9])
        logger.info('|-----------------------------------------------------------------|')

    # ------------------------------------------------------------------ #
    # accessors
    # ------------------------------------------------------------------ #

    def get_position(self, neighbor_id):
        return self.table[neighbor_id][0] if self.is_item(neighbor_id) else None

    def get_velocity(self, neighbor_id):
        return self.table[neighbor_id][1] if self.is_item(neighbor_id) else None

    def get_energy(self, neighbor_id):
        return self.table[neighbor_id][2] if self.is_item(neighbor_id) else None

    def get_role(self, neighbor_id):
        return self.table[neighbor_id][3] if self.is_item(neighbor_id) else None

    def get_cluster_id(self, neighbor_id):
        return self.table[neighbor_id][4] if self.is_item(neighbor_id) else None

    def get_cluster_head_id(self, neighbor_id):
        return self.table[neighbor_id][5] if self.is_item(neighbor_id) else None

    def get_cluster_epoch(self, neighbor_id):
        return self.table[neighbor_id][6] if self.is_item(neighbor_id) else None

    def get_nomination_count(self, neighbor_id):
        return self.table[neighbor_id][7] if self.is_item(neighbor_id) else None

    # ------------------------------------------------------------------ #
    # mobility similarity (section 11 of the spec)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, value))

    @classmethod
    def compute_similarity(cls, pos_a, vel_a, pos_b, vel_b):
        """
        S_ij = w_position * clip(1 - dist/R, 0, 1) + w_velocity * clip(1 - ||dV||/V_diff_max, 0, 1)
        """

        max_range = maximum_communication_range()
        distance = euclidean_distance_3d(pos_a, pos_b)
        position_similarity = cls._clamp01(1 - distance / max_range) if max_range > 0 else 0.0

        velocity_gap = euclidean_distance_3d(vel_a, vel_b)
        v_diff_max = config.MACG_MAX_VELOCITY_DIFFERENCE
        velocity_similarity = cls._clamp01(1 - velocity_gap / v_diff_max) if v_diff_max > 0 else 0.0

        similarity = (config.MACG_POSITION_WEIGHT * position_similarity +
                     config.MACG_VELOCITY_WEIGHT * velocity_similarity)

        return cls._clamp01(similarity)

    def similarity_to(self, neighbor_id):
        """Freshly recompute mobility similarity against a neighbor using this drone's current state"""

        if not self.is_item(neighbor_id):
            return None

        entry = self.table[neighbor_id]
        return self.compute_similarity(self.my_drone.coords, self.my_drone.velocity, entry[0], entry[1])

    def best_similarity_neighbor(self, exclude_ids=None):
        """
        Select the current neighbor with the highest (freshly-computed) mobility similarity.

        Tie breakers: higher residual energy, then lower node id (section 15 of the spec).

        :param exclude_ids: an optional iterable/set of neighbor ids to skip
        :return: the neighbor id, or None if there are no valid neighbors
        """

        exclude_ids = exclude_ids or set()
        best_id = None
        best_key = None

        for neighbor_id in list(self.table.keys()):
            if neighbor_id in exclude_ids or not self.is_item(neighbor_id):
                continue

            similarity = self.similarity_to(neighbor_id)
            energy = self.table[neighbor_id][2]
            key = (similarity, energy, -neighbor_id)  # maximize similarity, then energy, then minimize id

            if best_key is None or key > best_key:
                best_key = key
                best_id = neighbor_id

        return best_id

    # ------------------------------------------------------------------ #
    # Greedy candidate selection (section 30 of the spec)
    # ------------------------------------------------------------------ #

    def best_neighbor_towards(self, target_position, allowed_cluster_id=None, allowed_ids=None, excluded_ids=None):
        """
        Deterministic Greedy candidate selection toward an arbitrary target position.

        A candidate neighbor is only considered when it is strictly closer to "target_position"
        than "my_drone" currently is. Among the valid candidates, the closest one to the target is
        selected. No mobility/congestion/learning score is used here -- this is plain geographic
        Greedy, exactly as required by the spec.

        :param target_position: [x, y, z] position to route toward
        :param allowed_cluster_id: if set, only neighbors reporting this cluster_id are considered
        :param allowed_ids: if set, only neighbors whose id is in this collection are considered
        :param excluded_ids: if set, neighbors whose id is in this collection are skipped
        :return: identifier of the selected next hop, or "my_drone.identifier" if none qualifies
        """

        current_distance = euclidean_distance_3d(self.my_drone.coords, target_position)
        best_id = self.my_drone.identifier
        best_distance = current_distance

        for neighbor_id, entry in self.table.items():
            if not self.is_item(neighbor_id):
                continue
            if excluded_ids and neighbor_id in excluded_ids:
                continue
            if allowed_ids is not None and neighbor_id not in allowed_ids:
                continue
            if allowed_cluster_id is not None and entry[4] != allowed_cluster_id:
                continue

            distance = euclidean_distance_3d(entry[0], target_position)
            if distance < best_distance:
                best_distance = distance
                best_id = neighbor_id

        return best_id

    # ------------------------------------------------------------------ #
    # cross-cluster neighbor discovery (section 22-23 of the spec)
    # ------------------------------------------------------------------ #

    def cross_cluster_neighbors(self, own_cluster_id):
        """
        Group current one-hop neighbors that report a valid cluster id different from
        "own_cluster_id" by their (foreign) cluster id.

        :param own_cluster_id: this drone's own current cluster id (None if unclustered)
        :return: dict {neighbor_cluster_id: [(neighbor_id, similarity, entry), ...]}
        """

        groups = {}
        if own_cluster_id is None:
            return groups

        for neighbor_id, entry in self.table.items():
            if not self.is_item(neighbor_id):
                continue
            neighbor_cluster_id = entry[4]
            if neighbor_cluster_id is None or neighbor_cluster_id == own_cluster_id:
                continue

            similarity = self.similarity_to(neighbor_id)
            groups.setdefault(neighbor_cluster_id, []).append((neighbor_id, similarity, entry))

        return groups
