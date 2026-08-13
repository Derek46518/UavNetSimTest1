import math
import numpy as np
from routing.base.base_table import BaseTable


class QRoutingTable(BaseTable):
    def __init__(self, env, my_drone, rng_routing):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone
        self.q_table = 30000 * np.ones((my_drone.simulator.n_drones, my_drone.simulator.n_drones))  # initialization
        self.rng_routing = rng_routing

    def add_item(self, hello_packet, cur_time):
        """
        Update the neighbor table according to the hello packet
        :param hello_packet: the received hello packet
        :param cur_time: the moment when the packet is received
        :return: none
        """

        drone_id = hello_packet.src_drone.identifier
        position = hello_packet.cur_position

        self.table[drone_id] = [position, cur_time]

    # get the minimum Q-value of my neighbors
    def get_min_q_value(self, dst_drone_id):
        self.purge()

        min_q = 1e10  # initial value
        for neighbor in self.table.keys():
            min_q_temp = self.q_table[neighbor][dst_drone_id]
            if min_q_temp <= min_q:
                min_q = min_q_temp

        return min_q

    def best_neighbor(self, my_drone, dst_drone):
        """
        Choose the best next hop according to the Q-table
        :param my_drone: the drone that installed the GPSR
        :param dst_drone: the destination of the data packet
        :return: none
        """

        self.purge()

        dst_id = dst_drone.identifier

        if self.rng_routing.random() < 0.9 * math.pow(0.5, self.env.now / 1e6):
            best_id = self.rng_routing.choice(list(self.table.keys()))
        else:
            best_q_value = 1e10
            best_id = my_drone.identifier

            candidate_of_min_q_list = []

            for neighbor in self.table.keys():
                if neighbor != self.my_drone.identifier:  # cannot forward the packet to myself
                    next_hop_q_value = self.q_table[neighbor][dst_id]
                    if next_hop_q_value <= best_q_value:
                        best_q_value = next_hop_q_value

            for neighbor in self.table.keys():
                if neighbor != self.my_drone.identifier:
                    if self.q_table[neighbor][dst_id] == best_q_value:
                        candidate_of_min_q_list.append(neighbor)

            if len(candidate_of_min_q_list) != 0:
                best_id = self.rng_routing.choice(candidate_of_min_q_list)

        return best_id
