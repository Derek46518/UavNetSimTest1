import math
from simulator.log import logger
from utils import config
from utils.util_function import euclidean_distance_3d, euclidean_distance_2d


def sinr_calculator(my_drone, main_drones_list, all_transmitting_drones_list):
    """
    calculate signal to signal-to-interference-plus-noise ratio

    Parameters:
        my_drone: receiver drone
        main_drones_list: list of drones that wants to transmit packet to receiver
        all_transmitting_drones_list: list of all drones currently transmitting packet

    Returns:
        List of sinr of each main drone
    """

    simulator = my_drone.simulator
    transmit_power = config.TRANSMITTING_POWER
    noise_power = config.NOISE_POWER

    sinr_list = []  # record the sinr of all transmitter
    receiver = my_drone

    for pair in main_drones_list:  # each pair includes the main drone id and the channel id
        main_drone_id = pair[0]  # drone id of main transmitter
        channel_id = pair[1]  # channel id of main transmitter
        transmitter = simulator.drones[main_drone_id]

        interference_list = [x[0] for x in all_transmitting_drones_list]
        channel_list = [x[1] for x in all_transmitting_drones_list]

        main_link_path_loss = general_path_loss(receiver, transmitter)
        receive_power = transmit_power * main_link_path_loss
        interference_power = 0

        real_interference_nodes = []

        for i in range(0, len(interference_list)):
            if interference_list[i] != main_drone_id:  # possible interference
                if my_drone.channel_assigner.adjacent_channel_interference_check(channel_id, channel_list[i]):
                    interference = simulator.drones[interference_list[i]]
                    real_interference_nodes.append(interference_list[i])

                    interference_link_path_loss = general_path_loss(receiver, interference)
                    interference_power += transmit_power * interference_link_path_loss
                else:
                    # it means that two sub-channel is non-overlapping
                    pass

        sinr = 10 * math.log10(receive_power / (noise_power + interference_power))

        if real_interference_nodes:
            logger.info('At time: %s (us) ---- Packets collision: Main node is: %s, interference node is: %s, ',
                        simulator.env.now, main_drone_id, real_interference_nodes)

            simulator.metrics.collision_num += 1
        else:
            pass

        logger.info('At time: %s (us) ---- The SINR of main link between UAV (Tx) %s and UAV (Rx) %s is: %s',
                    simulator.env.now, main_drone_id, receiver.identifier, sinr)

        sinr_list.append(sinr)

    return sinr_list


def general_path_loss(receiver, transmitter):
    """
    General path loss model of line-of-sight (LoS) channels without system loss

    References:
        [1] J. Sabzehali, et al., "Optimizing number, placement, and backhaul connectivity of multi-UAV networks," in
            IEEE Internet of Things Journal, vol. 9, no. 21, pp. 21548-21560, 2022.

    Parameters:
        receiver: the drone that receives the packet
        transmitter: the drone that sends the packet

    Returns:
        path loss
    """

    c = config.LIGHT_SPEED
    fc = config.CARRIER_FREQUENCY
    alpha = 2  # path loss exponent

    distance = euclidean_distance_3d(receiver.coords, transmitter.coords)

    if distance != 0:
        path_loss = (c / (4 * math.pi * fc * distance)) ** alpha
    else:
        path_loss = 1

    return path_loss

def probabilistic_los_path_loss(receiver, transmitter):
    """
    probabilistic loss mode

    References:
        [1] A. Al-Hourani, S. Kandeepan and S. Lardner, "Optimal LAP Altitude for Maximum Coverage," in IEEE Wireless
            Communications Letters, vol. 3, no. 6, pp. 569-572, 2014.
        [2] J. Sabzehali, et al., "Optimizing number, placement, and backhaul connectivity of multi-UAV networks," in
            IEEE Internet of Things Journal, vol. 9, no. 21, pp. 21548-21560, 2022.

    Parameters:
        receiver: the drone that receives the packet
        transmitter: the drone that sends the packet

    Returns:
        path loss
    """

    c = config.LIGHT_SPEED
    fc = config.CARRIER_FREQUENCY
    alpha = 2  # path loss exponent
    eta_los = 0.1
    eta_nlos = 21
    a = 4.88
    b = 0.429

    distance = euclidean_distance_3d(receiver.coords, transmitter.coords)
    horizontal_dist = euclidean_distance_2d(receiver, transmitter)
    vertical_dist = max(receiver.coords[2], transmitter.coords[2])

    elevation_angle = math.atan(horizontal_dist / vertical_dist) * 180 / math.pi

    los_prob = 1 / (1 + a * math.exp(-b * (elevation_angle - a)))
    nlos_prob = 1 - los_prob

    if distance != 0:
        path_loss_los = ((c / (4 * math.pi * fc * distance)) ** alpha) * (10 ** (eta_los / 10))
        path_loss_nlos = ((c / (4 * math.pi * fc * distance)) ** alpha) * (10 ** (eta_nlos / 10))
    else:
        path_loss_los = 1
        path_loss_nlos = 1

    path_loss = los_prob * path_loss_los + nlos_prob * path_loss_nlos
    return path_loss


def maximum_communication_range():
    c = config.LIGHT_SPEED
    fc = config.CARRIER_FREQUENCY
    alpha = config.PATH_LOSS_EXPONENT  # path loss exponent
    transmit_power_db = 10 * math.log10(config.TRANSMITTING_POWER)
    noise_power_db = 10 * math.log10(config.NOISE_POWER)
    snr_threshold_db = config.SNR_THRESHOLD

    path_loss_db = transmit_power_db - noise_power_db - snr_threshold_db

    max_comm_range = (c * (10 ** (path_loss_db / (alpha * 10)))) / (4 * math.pi * fc)

    return max_comm_range
