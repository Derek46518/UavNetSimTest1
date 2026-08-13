from entities.packet import Packet


class QMRHelloPacket(Packet):
    def __init__(self,
                 src_drone,
                 creation_time,
                 id_hello_packet,
                 hello_packet_length,
                 received_hello_packet_count,
                 simulator,
                 channel_id):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id=channel_id)

        self.src_drone = src_drone
        self.cur_position = src_drone.coords
        self.cur_velocity = src_drone.velocity
        self.remain_energy = src_drone.residual_energy
        self.received_hello_packet_count = received_hello_packet_count

class QMRAckPacket(Packet):
    def __init__(self,
                 src_drone,
                 dst_drone,
                 ack_packet_id,
                 ack_packet_length,
                 ack_packet,
                 transmitting_start_time,
                 queuing_delay,
                 max_q,
                 is_local_minimum,
                 simulator,
                 source_packet_backoff_start_time,
                 channel_id,
                 creation_time=None
                 ):
        super().__init__(ack_packet_id, ack_packet_length, creation_time, simulator, channel_id=channel_id)

        self.src_drone = src_drone
        self.dst_drone = dst_drone

        self.ack_packet = ack_packet
        self.transmitting_start_time = transmitting_start_time
        self.queuing_delay = queuing_delay
        self.max_q = max_q
        self.is_local_minimum = is_local_minimum
        self.source_packet_backoff_start_time = source_packet_backoff_start_time
