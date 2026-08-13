from simulator.log import logger
from utils import config
from utils.util_function import euclidean_distance_3d
from phy.large_scale_fading import maximum_communication_range
from routing.base.base_table import BaseTable


class MCNeighborTable(BaseTable):
    """
    Neighbor table of MC-Greedy (Mobility- and Congestion-Aware Greedy) routing

    Type of the neighbor table: dictionary
    The structure of the neighbor table is:
        {drone1: [position1, velocity1, queue_ratio1, updated_time1], ...}

    "updated_time" MUST stay the last element of each entry, since "BaseTable.get_updated_time()" relies on
    "self.table[drone_id][-1]" to retrieve it.

    Each item in the neighbor table has its lifetime, if the hello packet from a drone has not been received for
    more than a certain time, it can be considered that this drone has flown out of my communication range.
    Therefore, the item associated with this drone is removed from my neighbor table

    Attributes:
        env: simulation environment
        my_drone: the drone that keeps this table
        have_void_area: used to indicate if encounters void area

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/1/11
    Updated at: 2026/3/10
    """

    def __init__(self, env, my_drone):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone
        self.have_void_area = 1

    def add_item(self, hello_packet, cur_time):
        """
        Update the neighbor table according to the received MC-Greedy hello packet
        :param hello_packet: the received hello packet (MCHelloPacket)
        :param cur_time: the moment when the packet is received
        :return: None
        """

        drone_id = hello_packet.src_drone.identifier
        self.table[drone_id] = [
            hello_packet.cur_position,
            hello_packet.cur_velocity,
            hello_packet.queue_ratio,
            cur_time,
        ]

    # get the position of a neighbor node
    def get_neighbor_position(self, certain_drone):
        if self.is_item(certain_drone):
            drone_id = certain_drone.identifier
            return self.table[drone_id][0]  # return the position list
        else:
            raise RuntimeError('This drone is not my neighbor!')

    # print neighbor table
    def print_item(self, my_drone):
        logger.info('|----------Neighbor Table of: %s ----------|', my_drone.identifier)
        for key in self.table:
            logger.info('Neighbor: %s, position is: %s, velocity is: %s, queue ratio is: %s, updated time is: %s, ',
                         key, self.table[key][0], self.table[key][1], self.table[key][2], self.table[key][3])
        logger.info('|-----------------------------------------------------------------|')

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def _predict_future_position(position, velocity, prediction_time):
        return [position[i] + velocity[i] * prediction_time for i in range(3)]

    def _calculate_progress(self, current_distance, neighbor_distance, max_range):
        progress = (current_distance - neighbor_distance) / max_range
        return self._clamp01(progress)

    def _calculate_stability(self, my_drone, neighbor_position, neighbor_velocity, max_range):
        prediction_time = config.MC_GREEDY_PREDICTION_TIME

        my_future_position = self._predict_future_position(my_drone.coords, my_drone.velocity, prediction_time)
        neighbor_future_position = self._predict_future_position(neighbor_position, neighbor_velocity, prediction_time)

        future_distance = euclidean_distance_3d(my_future_position, neighbor_future_position)
        stability = 1 - future_distance / max_range
        return self._clamp01(stability)

    def best_neighbor(self, my_drone, dst_drone):
        """
        Choose the best next hop according to the neighbor table

        A candidate neighbor is only considered when it makes positive geographic progress (i.e., it is strictly
        closer to the destination than the current UAV). Among the valid candidates, the one with the highest
        weighted score of geographic progress, predicted mobility/link stability and reported queue congestion is
        selected.

        :param my_drone: the drone that installed MC-Greedy
        :param dst_drone: the destination of the data packet
        :return: identifier of the selected next hop, or "my_drone.identifier" if no valid candidate exists
        """

        current_distance = euclidean_distance_3d(my_drone.coords, dst_drone.coords)
        max_range = maximum_communication_range()

        best_id = my_drone.identifier
        best_score = float('-inf')

        for neighbor_id, entry in self.table.items():
            neighbor_position = entry[0]
            neighbor_velocity = entry[1]
            queue_ratio = entry[2]

            neighbor_distance = euclidean_distance_3d(neighbor_position, dst_drone.coords)

            # preserve the original greedy forward-progress rule
            if neighbor_distance >= current_distance:
                continue

            progress = self._calculate_progress(current_distance, neighbor_distance, max_range)
            stability = self._calculate_stability(my_drone, neighbor_position, neighbor_velocity, max_range)
            congestion = self._clamp01(queue_ratio)

            score = (config.MC_GREEDY_PROGRESS_WEIGHT * progress +
                     config.MC_GREEDY_STABILITY_WEIGHT * stability -
                     config.MC_GREEDY_CONGESTION_WEIGHT * congestion)

            logger.debug('MC-Greedy candidate for UAV: %s -> neighbor: %s, progress: %s, stability: %s, '
                         'congestion: %s, score: %s',
                         my_drone.identifier, neighbor_id, progress, stability, congestion, score)

            if score > best_score:
                best_score = score
                best_id = neighbor_id
                self.have_void_area = 0

        logger.debug('MC-Greedy selected next hop for UAV: %s -> %s (score: %s)',
                     my_drone.identifier, best_id, best_score)

        return best_id
