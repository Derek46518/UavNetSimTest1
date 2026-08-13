from entities.packet import Packet


class MCHelloPacket(Packet):
    """
    Hello packet of MC-Greedy routing

    In addition to the sender's position (as in plain Greedy), this hello packet also snapshots the sender's
    current velocity and queue utilization, so that receiving neighbors can evaluate mobility stability and
    congestion when performing next-hop selection.

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/1/11
    Updated at: 2026/3/10
    """

    def __init__(self,
                 src_drone,
                 creation_time,
                 id_hello_packet,
                 hello_packet_length,
                 simulator,
                 channel_id):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id)

        self.src_drone = src_drone
        self.cur_position = list(src_drone.coords)
        self.cur_velocity = list(src_drone.velocity)

        if src_drone.max_queue_size > 0:
            queue_ratio = src_drone.transmitting_queue.qsize() / src_drone.max_queue_size
        else:
            queue_ratio = 0.0  # defensive fallback

        self.queue_ratio = max(0.0, min(1.0, queue_ratio))
