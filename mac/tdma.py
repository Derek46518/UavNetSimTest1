import simpy
import random
from simulator.log import logger
from phy.phy import Phy
from utils import config


class Tdma:
    """
    Medium access control protocol: TDMA (Time Division Multiple Access) following IEEE 802.11

    The basic flow of TDMA is as follows:
        1) Time is divided into frames, and each frame is divided into time slots
        2) Each node is assigned one or more time slots within a frame
        3) A node can only transmit during its assigned time slot(s)
        4) The node must wait for its slot even if the channel is idle
        5) ACK is sent in the same slot or in a designated ACK period

    Main attributes:
        my_drone: the drone that installed the TDMA protocol
        simulator: the simulation platform that contains everything
        rng_mac: a Random class for generating random numbers
        env: simulation environment created by simpy
        phy: the installed physical layer
        channel_states: used to determine if the channel is idle
        enable_ack: use ack or not
        slot_assignment: dictionary mapping drone IDs to their assigned slots
        frame_duration: duration of one TDMA frame
        slot_duration: duration of one time slot
        current_slot: the current slot number in the frame

    References:
        [1] IEEE 802.11 Standard for Wireless LAN Medium Access Control (MAC) and
            Physical Layer (PHY) Specifications
        [2] A. Boukerche, "Algorithms and Protocols for Wireless, Mobile Ad Hoc Networks,"
            Wiley-IEEE Press, 2008.
        [3] C. E. Perkins, "Ad Hoc Networking," Addison-Wesley, 2001.

    Author: Github @hkphimanshukumar321, some modifications by Zihao Zhou
    Created at: 2026/1/13
    Updated at: 2026/1/20
    """

    def __init__(self, drone):
        self.my_drone = drone
        self.simulator = drone.simulator
        self.drone_id_dict = {i: None for i in range(config.NUMBER_OF_DRONES)}
        self.rng_mac = random.Random(self.my_drone.identifier + self.my_drone.simulator.seed + 5)
        self.env = drone.env
        self.phy = Phy(self)
        self.channel_states = self.simulator.channel_states
        self.enable_ack = True

        self.wait_ack_process_dict = dict()
        self.wait_ack_process_finish = dict()
        self.wait_ack_process_count = 0
        self.wait_ack_process = None

        # TDMA-specific attributes
        self.slot_duration = 6000  # default 6000 us
        self.slots_per_frame = 10  # default as 10 slots
        self.frame_duration = self.slot_duration * self.slots_per_frame
        self.guard_time = 10  # guard time in us

        # Slot assignment - can be static or dynamic
        self.slot_assignment = self._initialize_slot_assignment()

    def _initialize_slot_assignment(self):
        """
        Initialize slot assignments for all drones
        Strategy: Round-robin assignment or can be customized
        :return: dictionary mapping drone_id to list of assigned slot numbers
        """
        slot_assignment = {}

        # Simple round-robin assignment
        for i in list(self.drone_id_dict.keys()):
            slot_assignment[i] = i % self.slots_per_frame

        logger.info('TDMA slot assignment initialized: %s', slot_assignment)
        return slot_assignment

    def _get_wait_time(self):
        """
        Calculate the start time of the next assigned slot for this drone
        :return: time to wait until next slot (in us)
        """

        my_slots = self.slot_assignment[self.my_drone.identifier]

        which_slot = self.env.now // self.slot_duration
        which_slot_in_frame = which_slot % self.slots_per_frame
        which_frame = which_slot // self.slots_per_frame

        start_time = which_frame * self.frame_duration + which_slot_in_frame * self.slot_duration
        end_time = start_time + self.slot_duration
        remaining_time = end_time - self.env.now

        if which_slot_in_frame == my_slots:
            if remaining_time <= 5000:
                to_wait = remaining_time + (self.slots_per_frame - 1) * self.slot_duration
            else:
                to_wait = 0
        else:
            if my_slots > which_slot_in_frame:
                # it means that this drone can send packet in this frame
                to_wait = remaining_time + (my_slots - which_slot_in_frame - 1) * self.slot_duration
            else:
                to_wait = remaining_time + (self.slots_per_frame - which_slot_in_frame - 1 + my_slots) * self.slot_duration

        return to_wait

    def mac_send(self, pkd):
        """
        Control when drone can send packet using TDMA
        :param pkd: the packet that needs to send
        :return: none
        """

        transmission_attempt = pkd.number_retransmission_attempt[self.my_drone.identifier]

        logger.info('At time: %s (us) ---- UAV: %s queues packet: %s for TDMA transmission (attempt: %s)',
                    self.env.now, self.my_drone.identifier, pkd.packet_id, transmission_attempt)

        # Wait for the assigned time slot
        time_to_slot = self._get_wait_time()

        logger.info('At time: %s (us) ---- UAV: %s must wait %s us for its time slot',
                    self.env.now, self.my_drone.identifier, time_to_slot)

        yield self.env.timeout(time_to_slot)

        # Add guard time at the beginning of the slot
        yield self.env.timeout(self.guard_time)

        if pkd.number_retransmission_attempt[self.my_drone.identifier] == 1:
            """
            Record the time when packet first attempts transmission
            """
            pkd.first_attempt_time = self.env.now

        key = ''.join(['mac_send', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
        self.my_drone.mac_process_finish[key] = 1  # mark the process as "finished"

        # Occupy the channel to send packet (in TDMA, collision is avoided by design)
        with self.channel_states[self.my_drone.identifier].request() as req:
            yield req

            logger.info('At time: %s (us) ---- UAV: %s transmits in its TDMA slot (pkd id: %s)',
                        self.env.now, self.my_drone.identifier, pkd.packet_id)

            pkd.transmitting_start_time = self.env.now
            transmission_mode = pkd.transmission_mode

            if transmission_mode == 0:  # for unicast
                next_hop_id = pkd.next_hop_id

                pkd.increase_ttl()
                self.phy.unicast(pkd, next_hop_id)
                yield self.env.timeout(pkd.packet_length / config.BIT_RATE * 1e6)  # transmission delay

                logger.info('At time: %s (us) ---- UAV: %s starts to wait ACK for packet: %s',
                            self.env.now, self.my_drone.identifier, pkd.packet_id)

                if self.enable_ack:
                    key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])

                    self.wait_ack_process = self.env.process(self.wait_ack(pkd))
                    self.wait_ack_process_dict[key2] = self.wait_ack_process
                    self.wait_ack_process_finish[key2] = 0

                    # Wait for ACK within the same slot (SIFS + ACK transmission time)
                    yield self.env.timeout(config.SIFS_DURATION + config.ACK_PACKET_LENGTH / config.BIT_RATE * 1e6)

            elif transmission_mode == 1:  # for broadcast
                pkd.increase_ttl()
                self.phy.broadcast(pkd)
                yield self.env.timeout(pkd.packet_length / config.BIT_RATE * 1e6)

        # Verify we didn't exceed slot duration
        time_in_slot = (self.env.now % self.frame_duration) % self.slot_duration
        if time_in_slot > self.slot_duration - self.guard_time:
            logger.warning('At time: %s (us) ---- UAV: %s transmission exceeded slot boundary!',
                           self.env.now, self.my_drone.identifier)

    def wait_ack(self, pkd):
        """
        If ACK is received within the specified time, the transmission is successful, otherwise,
        a re-transmission will be scheduled for the next available slot
        :param pkd: the data packet that waits for ACK
        :return: none
        """
        try:
            yield self.env.timeout(config.ACK_TIMEOUT)
            self.my_drone.routing_protocol.penalize(pkd)

            logger.info('At time: %s (us) ---- ACK timeout of packet: %s in TDMA slot',
                        self.env.now, pkd.packet_id)

            if pkd.number_retransmission_attempt[self.my_drone.identifier] < config.MAX_RETRANSMISSION_ATTEMPT:
                # Re-queue packet for transmission in next available slot
                yield self.env.process(self.my_drone.packet_coming(pkd))
            else:
                self.simulator.metrics.mac_delay.append((self.simulator.env.now - pkd.first_attempt_time) / 1e3)

                key2 = ''.join(['wait_ack', str(self.my_drone.identifier), '_', str(pkd.packet_id)])
                self.my_drone.mac_protocol.wait_ack_process_finish[key2] = 1

                logger.info('At time: %s (us) ---- Packet: %s is dropped after max retransmissions!',
                            self.env.now, pkd.packet_id)

        except simpy.Interrupt:
            # receive ACK in time
            logger.info('At time: %s (us) ---- UAV: %s receives the ACK for data packet: %s',
                        self.env.now, self.my_drone.identifier, pkd.packet_id)
