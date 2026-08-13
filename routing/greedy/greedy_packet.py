from entities.packet import Packet


class GreedyHelloPacket(Packet):
    def __init__(self,
                 src_drone,
                 creation_time,
                 id_hello_packet,
                 hello_packet_length,
                 simulator,
                 channel_id):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id)

        self.src_drone = src_drone
        self.cur_position = src_drone.coords
