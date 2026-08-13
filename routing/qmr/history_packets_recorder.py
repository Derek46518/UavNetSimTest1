from routing.qmr import qmr_config


class HistoryPacketsRecorder:
    def __init__(self, n_drones):
        self.n_drones = n_drones  # total number of drones in the network

        self.history_sent_data_packets = {}  # key: action_id, value: (packet, arrival_time)
        self.history_sent_hello_packets = []  # since hello pkt is broadcast, there is no key

        # key: source_id, value: (packet, arrival_time)
        self.history_received_ack_packets = {}
        self.history_received_hello_packets = {}

        self.init_recorder_for_all_ids()

    def init_recorder_for_all_ids(self):
        for i in range(self.n_drones):
            self.history_sent_data_packets[i] = []
            self.history_received_ack_packets[i] = []
            self.history_received_hello_packets[i] = []

    def add_sent_data_packet(self, data_packet):   #need to add “self.routing_protocol.history_packet_recorder.add_sent_data_packet(final_packet)” into drone.py (function feed_packet())
        """Add a record when a drone sends a data packet"""

        next_hop_id = data_packet.next_hop_id
        if next_hop_id not in self.history_sent_data_packets:
            self.history_sent_data_packets[next_hop_id] = []

        self.history_sent_data_packets[next_hop_id].append((data_packet, data_packet.creation_time))

    def add_sent_hello_packet(self, hello_packet):
        """Add a record when a drone broadcasts a hello packet"""

        self.history_sent_hello_packets.append((hello_packet, hello_packet.creation_time))

    def add_received_ack_packet(self, ack_packet):
        source_id = ack_packet.src_drone.identifier
        if source_id not in self.history_received_ack_packets:
            self.history_received_ack_packets[source_id] = []

        self.history_received_ack_packets[source_id].append((ack_packet, ack_packet.creation_time))

    def add_received_hello_packet(self, hello_packet):
        """Add a record when a drone receives a hello packet from its neighbor"""

        source_id = hello_packet.src_drone.identifier
        if source_id not in self.history_received_hello_packets:
            self.history_received_hello_packets[source_id] = []

        self.history_received_hello_packets[source_id].append((hello_packet, hello_packet.creation_time))

    def get_active_sent_data_packet_count(self, next_hop_id, cur_time):
        data_packet_list = self.history_sent_data_packets[next_hop_id]
        # 为了防止删除老数据包时影响了其他无人机的计算需求, 这里删除数据包时将起始时间调的更早一点
        active_packet_begin_time = cur_time - qmr_config.history_packet_life_time * 2
        clear_old_packet(data_packet_list, active_packet_begin_time)
        active_packet_begin_time = cur_time - qmr_config.history_packet_life_time
        return count_without_newer_packet(data_packet_list, active_packet_begin_time, cur_time)

    def get_sent_hello_packet_between_count(self, begin_time, end_time):
        count = 0
        for hello_packet, packet_time in self.history_sent_hello_packets:
            if packet_time < begin_time:
                continue
            if packet_time < end_time:
                count += 1
            if packet_time >= end_time:
                break
        return count

    def get_active_received_ack_packet_count(self, source_id, cur_time):
        ack_packet_list = self.history_received_ack_packets[source_id]
        active_packet_begin_time = cur_time - qmr_config.history_packet_life_time * 2
        clear_old_packet(ack_packet_list, active_packet_begin_time)
        active_packet_begin_time = cur_time - qmr_config.history_packet_life_time
        return count_without_newer_packet(ack_packet_list, active_packet_begin_time, cur_time)

    def get_all_active_received_hello_packet_count(self, cur_time):
        all_received_hello_packet_count = {}
        active_packet_begin_time = cur_time - qmr_config.history_packet_life_time * 2
        for source_id, hello_tuple_list in self.history_received_hello_packets.items():
            clear_old_packet(hello_tuple_list, active_packet_begin_time)
            all_received_hello_packet_count[source_id] = (
                count_and_found_most_early_time(hello_tuple_list, active_packet_begin_time, cur_time))
        return all_received_hello_packet_count

    def clear_received_packets_for_neighbor(self, neighbor_id):
        self.history_received_ack_packets[neighbor_id] = []
        self.history_received_hello_packets[neighbor_id] = []

def clear_old_packet(packet_time_tuple_list, begin_time):
    if len(packet_time_tuple_list) == 0:
        return

    while packet_time_tuple_list[0][1] < begin_time:
        packet_time_tuple_list.pop(0)
        if len(packet_time_tuple_list) == 0:
            break

def count_without_newer_packet(packet_time_tuple_list, begin_time, cur_time):
    count = 0
    for packet, packet_time in packet_time_tuple_list:
        if packet_time < begin_time:
            continue
        if packet_time <= cur_time:
            count += 1
        if packet_time > cur_time:
            break
    return count

def count_and_found_most_early_time(packet_time_tuple_list, begin_time, cur_time):
    count = 0
    most_early_time = None
    most_late_time = None
    for packet, packet_time in packet_time_tuple_list:
        if packet_time < begin_time:
            continue
        if packet_time < cur_time:
            count += 1
            if most_early_time is None:
                most_early_time = packet_time
            most_late_time = packet_time + 1
        if packet_time >= cur_time:
            break
    if most_early_time is None:
        most_early_time = 0
    if most_late_time is None:
        most_late_time = 0
    return count, most_early_time, most_late_time
