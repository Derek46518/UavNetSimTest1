from simulator.log import logger
from utils.util_function import euclidean_distance_3d
from routing.base.base_table import BaseTable


class GreedyNeighborTable(BaseTable):
    """
    Neighbor table of greedy forwarding

    Type of the neighbor table: dictionary
    The structure of the neighbor table is: {drone1: [coords1, updated time1], drone2: [coords2, updated time2],...}
    Each item in the neighbor table has its lifetime, if the hello packet from a drone has not been received for more
    than a certain time, it can be considered that this drone has flown out of my communication range. Therefore, the
    item associated with this drone is removed from my neighbor table

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
        Update the neighbor table according to the hello packet
        :param hello_packet: the received hello packet
        :param cur_time: the moment when the packet is received
        :return: None
        """

        drone_id = hello_packet.src_drone.identifier
        position = hello_packet.cur_position
        self.table[drone_id] = [position, cur_time]

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
            logger.info('Neighbor: %s, position is: %s, updated time is: %s, ',
                         key, self.table[key][0], self.table[key][1])
        logger.info('|-----------------------------------------------------------------|')

    def best_neighbor(self, my_drone, dst_drone):
        """
        Choose the best next hop according to the neighbor table
        :param my_drone: the drone that installed the GPSR
        :param dst_drone: the destination of the data packet
        :return: none
        """

        best_distance = euclidean_distance_3d(my_drone.coords, dst_drone.coords)
        best_id = my_drone.identifier

        for key in self.table.keys():
            next_hop_position = self.table[key][0]
            temp_distance = euclidean_distance_3d(next_hop_position, dst_drone.coords)
            if temp_distance < best_distance:
                best_distance = temp_distance
                best_id = key
                self.have_void_area = 0

        return best_id
