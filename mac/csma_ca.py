import simpy
import random
from simulator.log import logger
from phy.phy import Phy
from entities.packet import RtsPacket, CtsPacket
from utils import config
from utils.util_function import check_channel_availability


class CsmaCa:
    """
    Medium access control protocol: CSMA/CA (Carrier Sense Multiple Access With Collision Avoidance) without RTS/CTS

    The basic flow of the basic CSMA/CA (without RTS/CTS) is as follows:
        1) when a node has a packet to send, it first needs to wait until the channel is idle
        2) when the channel is idle, the node starts a timer and waits for "DIFS+backoff" periods of time, where the
           length of backoff is related to the number of re-transmissions
        3) if the entire decrement of the timer to 0 is not interrupted, then the node can occupy the channel and start
           sending the data packet and waiting for the corresponding ACK
        4) if the countdown is interrupted, it means that the node loses the game. The node should freeze the timer and
           wait for channel idle again before re-starting its timer

    Main attributes:
        my_drone: the drone that installed the CSMA/CA protocol
        simulator: the simulation platform that contains everything
        rng_mac: a Random class based on which we can call the function that generates the random number
        env: simulation environment created by simpy
        phy: the installed physical layer
        channel_states: used to determine if the channel is idle
        enable_ack: use ack or not

    References:
        [1] J. Li, et al., "Packet Delay in UAV Wireless Networks Under Non-saturated Traffic and Channel Fading
            Conditions," Wireless Personal Communications, vol. 72, no. 2, pp. 1105-1123, 2013.
        [2] M. A. Siddique and J. Kamruzzaman, "Performance Analysis of M-Retry BEB Based DCF Under Unsaturated Traffic
            Condition," in 2010 IEEE Wireless Communication and Networking Conference, 2010, pp. 1-6.
        [3] F. Daneshgaran, M. Laddomada, F. Mesiti and M. Mondin, "Unsaturated Throughput Analysis of IEEE 802.11 in
            Presence of Non-ideal Transmission Channel and Capture Effects," IEEE transactions on Wireless Communications
            vol. 7, no. 4, pp. 1276-1286, 2008.
        [4] Park, Ki hong, "Wireless Lecture Notes". Purdue. Retrieved 28 September 2012, link:
            https://www.cs.purdue.edu/homes/park/cs536-wireless-3.pdf

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/1/11
    Updated at: 2025/4/15
    """

    def __init__(self, drone):
        self.my_drone = drone
        self.simulator = drone.simulator
        self.rng_mac = random.Random(self.my_drone.identifier + self.my_drone.simulator.seed + 5)
        self.env = drone.env
        self.phy = Phy(self)
        self.channel_states = self.simulator.channel_states
        self.enable_ack = True
        self.enable_rts_cts = config.ENABLE_RTS_CTS

        self.wait_ack_process_dict = dict()
        self.wait_ack_process_finish = dict()
        self.wait_ack_process_count = 0
        self.wait_ack_process = None

        self.wait_cts_process_dict = dict()
        self.wait_cts_process_finish = dict()
        self.wait_cts_process = None

    def mac_send(self, pkd):
        """
        Control when drone can send packet
        :param pkd: the packet that needs to send
        :return: none
        """

        transmission_attempt = pkd.number_retransmission_attempt[self.my_drone.identifier]
        contention_window = (config.CW_MIN + 1) * (2 ** (transmission_attempt-1)) - 1

        backoff = self.rng_mac.randint(0, contention_window - 1) * config.SLOT_DURATION  # random backoff, in us
        to_wait = config.DIFS_DURATION + backoff

        logger.info('At time: %s (us) ---- UAV: %s sets its back-off counter as: %s',
                    self.env.now, self.my_drone.identifier, backoff)

        while to_wait:
            # wait until the channel becomes idle
            yield self.env.process(self.wait_idle_channel(self.my_drone, self.simulator.drones))

            if pkd.number_retransmission_attempt[self.my_drone.identifier] == 1:
                """
                NOTE: because the service time of the packet is given by the interval between the time when this packet
                starts backoff and the time when it is acknowledged and removed from the queue, so the "backoff_start_
                time" should be recorded only when the drone transmits this packet for the first time.
                """
                pkd.first_attempt_time = self.env.now

            # start listen the channel at backoff stage
            self.env.process(self.listen(self.channel_states, self.simulator.drones, pkd))

            logger.info('At time: %s (us) ---- UAV: %s should wait for %s to countdown its back-off counter',
                        self.env.now, self.my_drone.identifier, to_wait)
            start_time = self.env.now  # start to wait

            try:
                yield self.env.timeout(to_wait)
                to_wait = 0  # to break the while loop

                key = ''.join(['mac_send', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

                self.my_drone.mac_process_finish[key] = 1  # mark the process as "finished"

                # occupy the channel to send packet
                with self.channel_states[self.my_drone.identifier].request() as req:
                    yield req

                    logger.info('At time: %s (us) ---- UAV: %s can send packet (pkd id: %s)',
                                self.env.now, self.my_drone.identifier, pkd.packet_id)

                    pkd.transmitting_start_time = self.env.now
                    transmission_mode = pkd.transmission_mode

                    if transmission_mode == 0:  # for unicast
                        next_hop_id = pkd.next_hop_id

                        if self.enable_rts_cts:
                            cts_received = yield self.env.process(self.rts_cts_handshake(pkd, next_hop_id))

                            if not cts_received:
                                logger.info('At time: %s (us) ---- UAV: %s gives up packet: %s after RTS/CTS failure',
                                            self.env.now, self.my_drone.identifier, pkd.packet_id)

                                # spawn as a detached process (not yielded) so the "with" block below releases
                                # channel_states right away instead of holding it while a brand new mac_send
                                # attempt -- spawned deeper inside packet_coming -- tries to re-acquire the very
                                # same resource, which would otherwise deadlock
                                self.env.process(self._retransmit_or_drop(pkd))
                                return

                        pkd.increase_ttl()
                        self.phy.unicast(pkd, next_hop_id)  # note: unicast function should be executed first!
                        yield self.env.timeout(pkd.packet_length / config.BIT_RATE * 1e6)  # transmission delay

                        # only unicast data packets need to wait for ACK
                        logger.info('At time: %s (us) ---- UAV: %s starts to wait ACK for packet: %s',
                                    self.env.now, self.my_drone.identifier, pkd.packet_id)

                        if self.enable_ack:
                            # used to identify the process of waiting ack
                            key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

                            self.wait_ack_process = self.env.process(self.wait_ack(pkd))
                            self.wait_ack_process_dict[key2] = self.wait_ack_process
                            self.wait_ack_process_finish[key2] = 0  # indicate that this process hasn't finished

                            # continue to occupy the channel to prevent the ACK from being interfered
                            yield self.env.timeout(config.SIFS_DURATION + config.ACK_PACKET_LENGTH / config.BIT_RATE * 1e6)

                    elif transmission_mode == 1:
                        pkd.increase_ttl()
                        self.phy.broadcast(pkd)
                        yield self.env.timeout(pkd.packet_length / config.BIT_RATE * 1e6)

            except simpy.Interrupt:
                already_wait = self.env.now - start_time
                logger.info('At time: %s (us) ---- The back-off process of UAV: %s was interrupted, it has been waiting'
                            ' for: %s, original to_wait is: %s',
                            self.env.now, self.my_drone.identifier, already_wait, to_wait)

                to_wait -= already_wait  # the remaining waiting time

                if to_wait > backoff:
                    # interrupted in the process of DIFS
                    to_wait = config.DIFS_DURATION + backoff
                else:
                    # interrupted in the process of backoff, freeze the backoff
                    backoff = to_wait  # remaining backoff time
                    to_wait = config.DIFS_DURATION + backoff

    def wait_ack(self, pkd):
        """
        If ACK is received within the specified time, the transmission is successful, otherwise,
        a re-transmission will be originated
        :param pkd: the data packet that waits for ACK
        :return: none
        """

        try:
            yield self.env.timeout(config.ACK_TIMEOUT)

            logger.info('At time: %s (us) ---- ACK timeout of packet: %s',
                        self.env.now, pkd.packet_id)

            dropped = yield self.env.process(self._retransmit_or_drop(pkd))

            if dropped:
                key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
                self.wait_ack_process_finish[key2] = 1

        except simpy.Interrupt:
            # receive ACK in time
            logger.info('At time: %s (us) ---- UAV: %s receives the ACK for data packet: %s',
                        self.env.now, self.my_drone.identifier, pkd.packet_id)

    def _retransmit_or_drop(self, pkd):
        """
        Common failure path for a unicast attempt that did not complete (ACK timeout, or no CTS received):
        either hand the packet back for another attempt, or give up once the retry budget is exhausted.
        :param pkd: the data packet whose transmission attempt failed
        :return: True if the packet was dropped, False if a re-transmission was scheduled
        """

        self.my_drone.routing_protocol.penalize(pkd)

        if pkd.number_retransmission_attempt[self.my_drone.identifier] < config.MAX_RETRANSMISSION_ATTEMPT:
            yield self.env.process(self.my_drone.packet_coming(pkd))
            return False
        else:
            self.simulator.metrics.mac_delay.append((self.simulator.env.now - pkd.first_attempt_time) / 1e3)

            logger.info('At time: %s (us) ---- Packet: %s is dropped!',
                        self.env.now, pkd.packet_id)
            return True

    def rts_cts_handshake(self, pkd, next_hop_id):
        """
        Perform an RTS/CTS handshake with the intended next hop before actually transmitting a unicast data
        packet. This lets the receiver reserve the channel around itself (see reply_cts), protecting the
        upcoming data/ack exchange from senders that the original sender itself cannot sense (hidden terminals).
        :param pkd: the data packet that is about to be sent
        :param next_hop_id: the identifier of the intended receiver
        :return: True if a CTS was received in time, False otherwise
        """

        config.GL_ID_RTS_PACKET += 1
        rts_packet = RtsPacket(src_drone=self.my_drone,
                               dst_drone=self.simulator.drones[next_hop_id],
                               rts_packet_id=config.GL_ID_RTS_PACKET,
                               rts_packet_length=config.RTS_PACKET_LENGTH,
                               pending_packet=pkd,
                               simulator=self.simulator,
                               channel_id=pkd.channel_id)
        rts_packet.increase_ttl()

        logger.info('At time: %s (us) ---- UAV: %s sends RTS to UAV: %s for packet: %s',
                    self.env.now, self.my_drone.identifier, next_hop_id, pkd.packet_id)

        self.phy.unicast(rts_packet, next_hop_id)
        yield self.env.timeout(rts_packet.packet_length / config.BIT_RATE * 1e6)

        key2 = ''.join(['wait_cts', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

        self.wait_cts_process = self.env.process(self.wait_cts(pkd))
        self.wait_cts_process_dict[key2] = self.wait_cts_process
        self.wait_cts_process_finish[key2] = 0  # indicate that this process hasn't finished

        cts_received = yield self.wait_cts_process
        self.wait_cts_process_finish[key2] = 1

        return cts_received

    def wait_cts(self, pkd):
        """
        Block until a CTS for "pkd" is received, or CTS_TIMEOUT elapses
        :param pkd: the data packet whose RTS is awaiting a CTS reply
        :return: True if interrupted by a matching CTS, False if it timed out
        """

        try:
            yield self.env.timeout(config.CTS_TIMEOUT)

            logger.info('At time: %s (us) ---- CTS timeout of packet: %s', self.env.now, pkd.packet_id)

            return False
        except simpy.Interrupt:
            logger.info('At time: %s (us) ---- UAV: %s receives the CTS for data packet: %s',
                        self.env.now, self.my_drone.identifier, pkd.packet_id)

            return True

    def handle_control_packet(self, packet, src_drone_id):
        """
        Shared MAC-layer entry point for RTS/CTS packets, meant to be called directly from the drone's
        receive() loop, before dispatching to the routing protocol. RTS/CTS is a pure link-layer mechanism,
        so no routing protocol needs (or should need) to know about it.
        :param packet: the received RtsPacket or CtsPacket
        :param src_drone_id: the drone that sent this control packet
        :return: none
        """

        if isinstance(packet, RtsPacket):
            # reply_cts holds the channel for the whole announced data/ack exchange (up to several ms); it must
            # run as a detached process rather than being yielded here, otherwise this drone's receive() loop
            # itself would go "deaf" to its own inbox for that entire window -- including the exact moment the
            # DATA packet it just agreed to receive is expected to arrive
            self.env.process(self.reply_cts(packet, src_drone_id))
        elif isinstance(packet, CtsPacket):
            self._unblock_wait_cts(packet, src_drone_id)

        yield self.env.timeout(0)

    def reply_cts(self, rts_packet, src_drone_id):
        """
        Reply with a CTS after receiving an RTS addressed to this drone, then hold the channel around this
        drone for the duration of the data/ack exchange that the RTS announced.
        :param rts_packet: the received RTS packet
        :param src_drone_id: the drone that sent the RTS
        :return: none
        """

        pending_packet = rts_packet.pending_packet

        yield self.env.timeout(config.SIFS_DURATION)  # switch from receiving to transmitting

        if self.my_drone.sleep:
            return

        config.GL_ID_CTS_PACKET += 1
        cts_packet = CtsPacket(src_drone=self.my_drone,
                               dst_drone=self.simulator.drones[src_drone_id],
                               cts_packet_id=config.GL_ID_CTS_PACKET,
                               cts_packet_length=config.CTS_PACKET_LENGTH,
                               pending_packet=pending_packet,
                               simulator=self.simulator,
                               channel_id=pending_packet.channel_id)
        cts_packet.increase_ttl()

        # reserve the channel around the receiver for the announced data/ack exchange: any third node that
        # cannot sense the original sender will still sense this drone as busy and defer, which is exactly
        # what protects against the hidden-terminal problem
        reservation = (cts_packet.packet_length / config.BIT_RATE * 1e6 + config.SIFS_DURATION +
                      pending_packet.packet_length / config.BIT_RATE * 1e6 + config.SIFS_DURATION +
                      config.ACK_PACKET_LENGTH / config.BIT_RATE * 1e6)

        with self.channel_states[self.my_drone.identifier].request() as req:
            yield req

            logger.info('At time: %s (us) ---- UAV: %s replies CTS to UAV: %s for packet: %s',
                        self.env.now, self.my_drone.identifier, src_drone_id, pending_packet.packet_id)

            self.phy.unicast(cts_packet, src_drone_id)
            yield self.env.timeout(reservation)

    def _unblock_wait_cts(self, cts_packet, src_drone_id):
        key2 = ''.join(['wait_cts', str(self.my_drone.identifier), '_', str(cts_packet.pending_packet.packet_id)])

        if self.wait_cts_process_finish.get(key2) == 0:
            if not self.wait_cts_process_dict[key2].triggered:
                logger.info('At time: %s (us) ---- wait_cts process (id: %s) of UAV: %s is interrupted by UAV: %s',
                            self.env.now, key2, self.my_drone.identifier, src_drone_id)

                self.wait_cts_process_finish[key2] = 1
                self.wait_cts_process_dict[key2].interrupt()

    def send_ack(self, ack_packet, dst_id):
        """
        Common "reply immediately after SIFS, without contending for the channel" delivery used for the ACK
        packet by every routing protocol.
        :param ack_packet: the constructed ACK (or protocol-specific ACK subclass) packet
        :param dst_id: the drone this ACK is replying to
        :return: none
        """

        yield self.env.timeout(config.SIFS_DURATION)  # switch from receiving to transmitting

        if not self.my_drone.sleep:
            ack_packet.increase_ttl()
            self.phy.unicast(ack_packet, dst_id)
            yield self.env.timeout(ack_packet.packet_length / config.BIT_RATE * 1e6)

    def unblock_wait_ack(self, data_packet_id, src_drone_id):
        """
        Common bookkeeping once an ACK has been received: unblocks the corresponding wait_ack process.
        Routing protocols should call this after they've finished any protocol-specific handling of the
        ACK's contents (e.g. updating a Q-table, recording mac delay).
        :param data_packet_id: packet_id of the data packet that was just acked
        :param src_drone_id: the drone the ACK came from
        :return: none
        """

        key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(data_packet_id)])

        if self.wait_ack_process_finish[key2] == 0:
            if not self.wait_ack_process_dict[key2].triggered:
                logger.info('At time: %s (us) ---- wait_ack process (id: %s) of UAV: %s is interrupted by UAV: %s',
                            self.env.now, key2, self.my_drone.identifier, src_drone_id)

                self.wait_ack_process_finish[key2] = 1
                self.wait_ack_process_dict[key2].interrupt()

    def wait_idle_channel(self, sender_drone, drones):
        """
        Wait until the channel becomes idle
        :param sender_drone: the drone that is about to send packet
        :param drones: a list, which contains all the drones in the simulation
        :return: none
        """

        while not check_channel_availability(self.channel_states, sender_drone, drones):
            yield self.env.timeout(config.SLOT_DURATION)

    def listen(self, channel_states, drones, pkd):
        """
        When the drone waits until the channel is idle, it starts its own timer to count down, in this time, the drone
        needs to detect the state of the channel during this period, and if the channel is found to be busy again, the
        countdown process should be interrupted
        :param channel_states: a dictionary, indicates the use of the channel by different drones
        :param drones: a list, contains all drones in the simulation
        :param pkd: listen to the channel for which packet
        :return: none
        """

        logger.info('At time: %s (us) ---- UAV: %s starts to listen the channel and perform back-off',
                     self.env.now, self.my_drone.identifier)

        key = ''.join(['mac_send', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

        while self.my_drone.mac_process_finish[key] == 0:  # interrupt only if the process is not complete
            if check_channel_availability(channel_states, self.my_drone, drones) is False:
                # found channel be occupied, start interrupt

                key = ''.join(['mac_send',str(self.my_drone.identifier),'_',str(pkd.packet_id)])
                if not self.my_drone.mac_process_dict[key].triggered:
                    self.my_drone.mac_process_dict[key].interrupt()
                    break
            else:
                pass

            yield self.env.timeout(1)
