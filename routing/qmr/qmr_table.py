import logging
import numpy as np
import random
from routing.qmr import qmr_config
from utils import config, util_function
from routing.base.base_table import BaseTable

logger = logging.getLogger("network_routing")

class QMRTable(BaseTable):
    def __init__(self, env, my_drone):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone

        """
        The structure of the neighbor table in QMR
        |    Drone id   |  1  |  2  |   3    |    4    | 5  |     6    |     7      |   8   |
        | neighbor_id 1 | pos | vec | energy | Q-value | LQ | cur_time | last_max_q | delay |
        | neighbor_id 2 | pos | vec | energy | Q-value | LQ | cur_time | last_max_q | delay |
        |       ...     | ... | ... |
        | neighbor_id N | pos | vec | energy | Q-value | LQ | cur_time | last_max_q | delay |
        """

        self.discount_factor = 0.5

        self.total_delay_recorder = {} # key: neighbor_id, value: list
        self.mac_delay_recorder = {} # key: neighbor_id, value: list(delay, generated time)
        self.queuing_delay_recorder = [] # list(delay, generated time)

        self.window_for_uniformed_delay = qmr_config.hello_interval * 10

        self.last_neighbor_set = None
        self.sliding_win_length_mac = 10
        self.sliding_win_length_queuing = 10
        self.max_length_delay = 10
        self.beta = 0.5
        self.omega = 0.5

    def add_new_neighbor_entry(self, drone_id):
        """Add a new entry in the neighbor table"""

        entry = {
            "recorded_pos": None,  # current position of the neighbor, according to the hello pkt
            "recorded_vel": None,  # current velocity of the neighbor
            "remain_energy": None,  # remaining energy of the neighbor
            "q_value": 0.5,  # initial Q-value of this action
            "weighted_q_value": 0.5,
            "lq": 1,  # link quality between the neighbor drone and myself
            "k_factor": 1,  # the weight of the Q-value
            "actual_vel": 0,
            "updated_time": None,  # the time at which the info of this neighbor is updated
            "last_max_q": None,
            "ld": 5, # s
            "delay": 5 * 1e5,
            "lr": 0.3,
            "dc": 0.5,
        }

        self.table[drone_id] = entry

    def update_neighbor(self, hello_packet, cur_time):
        """Update neighbor entry according to the incoming hello packet"""

        if hello_packet.src_drone.identifier != self.my_drone.identifier:
            neighbor_id = hello_packet.src_drone.identifier
            cur_pos = hello_packet.cur_position
            cur_vel = hello_packet.cur_velocity
            remain_energy = hello_packet.remain_energy
            lq = self.generate_lq(hello_packet, neighbor_id, hello_packet.received_hello_packet_count)

            if neighbor_id not in self.table:
                self.add_new_neighbor_entry(neighbor_id)

            entry = self.table[neighbor_id]
            entry["recorded_pos"] = cur_pos
            entry["recorded_vel"] = cur_vel
            entry["remain_energy"] = remain_energy
            entry["lq"] = lq
            entry["updated_time"] = cur_time

    def get_updated_time(self, drone_id):
        if drone_id not in self.table.keys():
            raise RuntimeError('This item is not in the neighbor table')
        else:
            return self.table[drone_id]["updated_time"]

    def generate_lq(self, hello_packet, neighbor_id, received_hello_count):
        """
        The link quality (lq) is calculated using the forward delivery ratios "df" and
        reverse delivery ratio "dr" of the link, where "df" represents the probability
        that a data packet successfully arrives at the recipient, and "df" represents
        the probability of sender successfully receiving ACK packets.

        Hello packet is used to measure "df" and "dr"

        Args:
            hello_packet: the incoming hello packet
            neighbor_id: the id of the drone which broadcasts the hello packet
            received_hello_count:

        Returns:

        """

        cur_time = hello_packet.creation_time
        history_packet_recorder = self.my_drone.routing_protocol.history_packet_recorder

        # df: it is defined as the number of HELLO packets successfully received by drone j from drone i within a
        # certain period of time divided by the total number of HELLO packets sent by drone i during this period
        received_hello_count_by_this_neighbor = received_hello_count[self.my_drone.identifier][0]
        received_hello_begin_time = received_hello_count[self.my_drone.identifier][1] - qmr_config.hello_interval / 2
        received_hello_end_time = received_hello_count[self.my_drone.identifier][2]
        sent_hello_count = history_packet_recorder.get_sent_hello_packet_between_count(
            received_hello_begin_time, received_hello_end_time)

        if sent_hello_count == 0:
            df = 1
        else:
            df = received_hello_count_by_this_neighbor / sent_hello_count

        # dr: it is defined as the number of ACK packets received by drone i from drone j within a certain period of
        # time divided by the number of data packets sent by drone i to drone j
        cur_time = self.env.now
        received_ack_count = history_packet_recorder.get_active_received_ack_packet_count(neighbor_id, cur_time)
        sent_data_count = history_packet_recorder.get_active_sent_data_packet_count(neighbor_id, cur_time)
        if sent_data_count == 0:
            dr = 1
        else:
            dr = received_ack_count / sent_data_count

        logger.info(f"uav: {self.my_drone.identifier}, "
                    f"neighbor: {neighbor_id}, "
                    f"df: {df}, "
                    f"received_hello_count_by_this_neighbor: {received_hello_count_by_this_neighbor}, "
                    f"sent_hello_count: {sent_hello_count}, "
                    f"dr: {dr}, "
                    f"received_ack_count: {received_ack_count}, "
                    f"sent_data_count: {sent_data_count}, "
                    f"cur_time: {cur_time}")

        # LQ = df * dr
        return df * dr

    def compute_actual_velocity_3d(self, neighbor_id, cur_time, i_dist_to_dest, dst_coords):
        """
        Calculate the actual velocity of the data packet from node i to its neighbor j

        Args:
            neighbor_id: the id of the neighbor drone
            cur_time: the current moment
            i_dist_to_dest: the distance between the real position of the node i at t2 and the destination
            dst_coords: the coordinates of the destination node

        Returns: actual velocity of the data packet
        """

        pos_x_j = self.table[neighbor_id]["recorded_pos"][0]
        pos_y_j = self.table[neighbor_id]["recorded_pos"][1]
        pos_z_j = self.table[neighbor_id]["recorded_pos"][2]
        v_x_j = self.table[neighbor_id]["recorded_vel"][0]
        v_y_j = self.table[neighbor_id]["recorded_vel"][1]
        v_z_j = self.table[neighbor_id]["recorded_vel"][2]

        # "t1" is the updated time of this entry
        t1 = self.table[neighbor_id]["updated_time"]

        # "t2" is the current moment
        t2 = cur_time

        delay = self.table[neighbor_id]["delay"]

        t3 = t2 + delay

        # predict the position of neighbor j
        pos_x_j_t3 = pos_x_j + v_x_j * ((t3 - t1) / 1e6)
        pos_y_j_t3 = pos_y_j + v_y_j * ((t3 - t1) / 1e6)
        pos_z_j_t3 = pos_z_j + v_z_j * ((t3 - t1) / 1e6)

        j_dist_to_dest = util_function.euclidean_distance_3d([pos_x_j_t3, pos_y_j_t3, pos_z_j_t3], dst_coords)

        actual_velocity = (i_dist_to_dest - j_dist_to_dest) / (delay / 1e6)

        return actual_velocity

    def add_mac_delay(self, mac_delay, cur_time, neighbor_id):
        """
        When a mac delay is measured, it is added into the "mac_delay_recorder"
        For a drone i with m neighbors, it always maintains m sliding windows with length n,
        each window records the MAC delay of the last n data packets sent by node i to node j.

        Args:
            mac_delay:
            cur_time: the current moment
            neighbor_id:

        Returns:

        """

        if neighbor_id not in self.mac_delay_recorder:
            self.mac_delay_recorder[neighbor_id] = []

        self.mac_delay_recorder[neighbor_id].append((mac_delay, cur_time))

        while len(self.mac_delay_recorder) > self.sliding_win_length_mac:
            # the oldest one will be deleted
            first_key = next(iter(self.mac_delay_recorder))
            self.mac_delay_recorder.pop(first_key)
        # self.add_delay(neighbor_id, cur_time)

    def add_queuing_delay(self, queuing_delay, cur_time):
        """When a queuing delay is measured, it is added into the queuing_delay_recorder"""

        self.queuing_delay_recorder.append((queuing_delay, cur_time))

        while len(self.queuing_delay_recorder) > self.sliding_win_length_queuing:
            self.queuing_delay_recorder.pop(0)  # the oldest one will be deleted

    def get_window_mean_mac_delay(self, neighbor_id):
        """Update MAC delay using exponentially weighted moving average"""

        if neighbor_id not in self.mac_delay_recorder:
            self.mac_delay_recorder[neighbor_id] = []

        delay_recorder = self.mac_delay_recorder[neighbor_id]
        return self.get_mean_delay(delay_recorder)

    def get_window_mean_queuing_delay(self):
        """Update queuing delay using exponentially weighted moving average"""

        delay_recorder = self.queuing_delay_recorder
        return self.get_mean_delay(delay_recorder)

    def get_mean_delay(self, delay_recorder):
        delay_list = [delay[0] for delay in delay_recorder]

        if len(delay_list) == 0:
            return 5*1e5
        elif len(delay_list) == 1:
            return delay_list[0]
        else:
            new_delay = delay_list[-1]
            return (1 - self.beta) * np.mean(delay_list) + self.beta * new_delay

    def update_delay(self, neighbor_id, cur_time):
        total_delay = self.get_window_mean_mac_delay(neighbor_id) + self.get_window_mean_queuing_delay()

        if neighbor_id not in self.total_delay_recorder:
            self.total_delay_recorder[neighbor_id] = []

        self.total_delay_recorder[neighbor_id].append(total_delay)

        while len(self.total_delay_recorder[neighbor_id]) > self.max_length_delay:
            self.total_delay_recorder[neighbor_id].pop(0)

        self.table[neighbor_id]["delay"] = total_delay

    def get_normalized_delay(self, neighbor_id):
        """Used in adaptively adjusting the learning rate"""

        if neighbor_id not in self.total_delay_recorder:
            self.total_delay_recorder[neighbor_id] = []

        delay_list = self.total_delay_recorder[neighbor_id]

        if len(delay_list) == 0 or len(delay_list) == 1:
            return 5*1e5  # 5ms in default

        mean_delay = np.mean(delay_list)
        standard_delay = np.std(delay_list)

        cur_delay = delay_list[-1]

        if standard_delay == 0:
            return -1
        else:
            normalized_delay = abs(cur_delay - mean_delay) / standard_delay
            return normalized_delay

    def get_reward(self, f, is_penalty, next_hop_id):
        if is_penalty:
            reward = -10
        elif f == 1:
            reward = 10
        else:
            delay = self.table[next_hop_id]["delay"] / 1e6
            neighbor_energy_factor = self.table[next_hop_id]["remain_energy"] / config.INITIAL_ENERGY
            reward = self.omega * np.exp(-delay) + (1 - self.omega) * neighbor_energy_factor
        return reward

    def get_max_q(self):
        if len(self.table) == 0:
            return 0
        return max([self.table[neighbor_id]["q_value"] for neighbor_id in self.table.keys()])

    def filter_space_of_exploration(self, packet, destination, cur_time):

        cur_neighbor_ids = self.table.keys()
        packet_deadline = (packet.creation_time + packet.deadline - cur_time) / 1e6

        # calculate the required velocity
        dist_to_dest = util_function.euclidean_distance_3d(self.my_drone.coords, destination.coords)
        required_velocity = dist_to_dest / packet_deadline

        candidate_neighbors = []
        sub_candidate_neighbors = []
        actual_velocity_dict = {}

        for neighbor_id in cur_neighbor_ids:
            # calculate the actual velocity of each neighbor
            neighbor_entry = self.table[neighbor_id]
            actual_velocity = self.compute_actual_velocity_3d(neighbor_id, cur_time, dist_to_dest, destination.coords)

            actual_velocity_dict[neighbor_id] = actual_velocity
            self.table[neighbor_id]["actual_velocity"] = actual_velocity

            if actual_velocity < required_velocity:
                sub_candidate_neighbors.append((neighbor_id, actual_velocity))
                continue

            neighbor_mobility_v = neighbor_entry["recorded_vel"]
            predicted_neighbor_position = [
                neighbor_entry["recorded_pos"][0] + neighbor_mobility_v[0] * (cur_time - neighbor_entry["updated_time"]) / 1e6,
                neighbor_entry["recorded_pos"][1] + neighbor_mobility_v[1] * (cur_time - neighbor_entry["updated_time"]) / 1e6,
                neighbor_entry["recorded_pos"][2]]
            dist_i_to_j = util_function.euclidean_distance_3d(self.my_drone.coords, predicted_neighbor_position)

            m = 0
            r = qmr_config.communication_range
            if dist_i_to_j <= r:
                m = 1 - (dist_i_to_j / r)

            lq = neighbor_entry["lq"]

            k = m * lq
            candidate_neighbors.append((neighbor_id, k))
            self.table[neighbor_id]["k_factor"] = k
            self.table[neighbor_id]["weighted_q_value"] = k * self.table[neighbor_id]["q_value"]

        return candidate_neighbors, sub_candidate_neighbors, actual_velocity_dict, required_velocity

    def route_decision_qmr(self, packet, destination):
        cur_time = self.env.now
        cur_neighbor_ids = self.table.keys()

        candidate_neighbors, sub_candidate_neighbors, actual_velocity_dict, min_velocity = (
            self.filter_space_of_exploration(packet, destination, cur_time))

        if len(candidate_neighbors) > 0:
            # find the best next hop that has the maximum Q-value
            chosen_neighbor_id = max(candidate_neighbors, key=lambda x: x[1] * self.table[x[0]]["q_value"])[0]

        elif len(sub_candidate_neighbors) > 0:
            chosen_neighbor_id = max(sub_candidate_neighbors, key=lambda x: x[1])[0]

        else:
            if len(cur_neighbor_ids) == 0:
                chosen_neighbor_id = self.my_drone.identifier
            else:
                chosen_neighbor_id = max(cur_neighbor_ids, key=lambda x: self.table[x]["q_value"])

        return chosen_neighbor_id

    def make_route_decision(self, packet, destination, eps=None):
        if qmr_config.which_exploration_mechanism == 'greedy':
            return self.route_decision_e_greedy(eps)
        elif qmr_config.which_exploration_mechanism == 'qmr':
            return self.route_decision_qmr(packet, destination)

    def route_decision_e_greedy(self, eps):
        self.purge()
        random_num = random.random()

        if random_num < eps:
            # exploration
            logger.info(f"uav: {self.my_drone.identifier}, blind search, current eps: {eps}, random num: {random_num}")
            if len(self.table) == 0:
                logger.info(f"uav: {self.my_drone.identifier}, no neighbor, return None")
                return None
            return random.choice(list(self.table.keys()))
        # exploitation
        logger.info(f"uav: {self.my_drone.identifier}, use the max q value, current eps: {eps}, random num: {random_num}")
        if len(self.table) == 0:
            logger.info(f"uav: {self.my_drone.identifier}, no neighbor, return None")
            return None
        return max(self.table.keys(), key=lambda x: self.table[x]["q_value"])

    def update_discounted_factor(self):
        self.discount_factor = 0.4

        # TODO: Implement the dynamic discounted factor
        return

    def update_q_value(self, f, max_q, next_hop_id, is_penalty, dst_drone=None):
        if next_hop_id not in self.table:
            return

        self.table[next_hop_id]["last_max_q"] = max_q
        q_value = self.table[next_hop_id]["q_value"]

        reward = self.get_reward(f, is_penalty, next_hop_id)

        normalized_delay = self.get_normalized_delay(next_hop_id)

        if normalized_delay == -1:
            lr = 0.3  # it means that the variance of one-hop delay is 0
        else:
            lr = max(0.3, 1 - np.exp(-normalized_delay))

        dc = self.discount_factor

        if max_q is None:
            # TODO: to check in which situation this condition will be triggered
            max_q = q_value

        q_value = q_value + lr * (reward + dc * max_q - q_value)

        self.table[next_hop_id]["q_value"] = q_value
        self.table[next_hop_id]["lr"] = lr
        self.table[next_hop_id]["dc"] = dc

    def check_local_minimum(self, destination):
        if self.my_drone.identifier == destination.identifier:
            return False
        my_pos = self.my_drone.coords
        dest_pos = destination.coords
        my_dist_to_dest = util_function.euclidean_distance_3d(my_pos, dest_pos)
        for neighbor_id in self.table.keys():
            neighbor_pos = self.table[neighbor_id]["recorded_pos"]
            neighbor_dist_to_dest = util_function.euclidean_distance_3d(neighbor_pos, dest_pos)
            if neighbor_dist_to_dest < my_dist_to_dest:
                return False
        return True
