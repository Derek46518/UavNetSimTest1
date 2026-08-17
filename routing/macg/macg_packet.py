from entities.packet import Packet


class MACGHelloPacket(Packet):
    """
    Hello packet of MACG (Mobility-Aware Clustered Greedy) routing

    In addition to the sender's position (as in plain Greedy), this hello packet snapshots the
    sender's current velocity, residual energy and clustering state (role / cluster id / CH id /
    cluster epoch), so that receiving neighbors can evaluate mobility similarity and keep their
    local view of the clustering topology up to date. "nomination_count" is also included: it is a
    small, locally-scoped extra field (the sender's own current nomination tally) that lets a
    neighbor run the deterministic CH fallback-election rule (section 17 of the spec) without
    inspecting any node's live cluster-manager state -- it only ever reads what was broadcast.

    All vector fields are plain copies of the source drone's state at creation time; nothing here
    is a live mutable reference that could change after the packet has been handed to the MAC layer.
    """

    def __init__(self,
                 src_drone,
                 creation_time,
                 id_hello_packet,
                 hello_packet_length,
                 simulator,
                 channel_id,
                 cluster_manager):
        super().__init__(id_hello_packet, hello_packet_length, creation_time, simulator, channel_id)

        self.src_drone = src_drone
        self.cur_position = list(src_drone.coords)
        self.cur_velocity = list(src_drone.velocity)
        self.residual_energy = src_drone.residual_energy

        self.role = cluster_manager.role
        self.cluster_id = cluster_manager.cluster_id
        self.cluster_head_id = cluster_manager.cluster_head_id
        self.cluster_epoch = cluster_manager.cluster_epoch
        self.nomination_count = cluster_manager.nomination_count

        self.timestamp = creation_time


class MACGControlPacket(Packet):
    """
    Generic MACG clustering control packet.

    A single explicit class is used for every clustering message (rather than one subclass per
    message type) since all of them share the same shape: an originator, an optional addressee
    ("dst_id"; "None" means the message is meant for every current listener, e.g. CH_DECLARE /
    MAINTENANCE), a "message_type" tag, and a small payload dictionary of already-copied plain
    values (never a live reference into another drone's mutable state).

    Supported message types (see the class-level constants below):
        NOMINATION, CH_DECLARE, JOIN_REQUEST, JOIN_ACCEPT, CLUSTER_STATE,
        MAINTENANCE, MAINT_RESPONSE, GATEWAY_UPDATE
    """

    NOMINATION = 'NOMINATION'
    CH_DECLARE = 'CH_DECLARE'
    JOIN_REQUEST = 'JOIN_REQUEST'
    JOIN_ACCEPT = 'JOIN_ACCEPT'
    CLUSTER_STATE = 'CLUSTER_STATE'
    MAINTENANCE = 'MAINTENANCE'
    MAINT_RESPONSE = 'MAINT_RESPONSE'
    GATEWAY_UPDATE = 'GATEWAY_UPDATE'

    def __init__(self,
                 src_drone,
                 dst_id,
                 creation_time,
                 id_packet,
                 packet_length,
                 message_type,
                 payload,
                 simulator,
                 channel_id):
        super().__init__(id_packet, packet_length, creation_time, simulator, channel_id)

        self.src_drone = src_drone
        self.dst_id = dst_id  # None => addressed to every current listener (broadcast announcement)
        self.message_type = message_type
        self.payload = payload
        self.timestamp = creation_time
