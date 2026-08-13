#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：UavNetSim
@File    ：qfanet_packet.py
@Author  ：abing xbb992@vip.qq.com
@Date    ：2025/8/20
@Update  ：2025/8/29
'''
from entities.packet import Packet


class QFanetHelloPacket(Packet):

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
        self.cur_velocity = src_drone.velocity
        self.src_energy = src_drone.residual_energy
        self.mobility_model = src_drone.mobility_model


class QFanetAckPacket(Packet):
    def __init__(self,
                 src_drone,
                 dst_drone,
                 ack_packet_id,
                 ack_packet_length,
                 acked_packet,
                 void_area_flag,
                 reward,
                 sinr_eta,
                 simulator,
                 channel_id,
                 creation_time=None):
        super().__init__(ack_packet_id, ack_packet_length, creation_time or simulator.env.now, simulator, channel_id)
        self.src_drone = src_drone
        self.src_coords = src_drone.coords
        self.src_velocity = src_drone.velocity
        self.dst_drone = dst_drone
        self.acked_packet = acked_packet
        self.void_area_flag = void_area_flag
        self.reward = reward
        self.sinr_eta = sinr_eta
