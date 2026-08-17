import logging
from utils.ieee_802_11 import IeeeStandard

IEEE_802_11 = IeeeStandard().b_802_11

# --------------------- simulation parameters --------------------- #
MAP_LENGTH = 600  # m, length of the map
MAP_WIDTH = 600  # m, width of the map
MAP_HEIGHT = 100  # m, height of the map
SIM_TIME = 30 * 1e6  # us, total simulation time
NUMBER_OF_DRONES = 10  # number of drones in the network
GRID_RESOLUTION = 20  # grid the map for path planning
STATIC_CASE = 0  # whether to simulate a static network
HETEROGENEOUS = 0  # heterogeneous network support (in terms of speed)
DRONE_SPEED = 10  # m/s, homogeneous drone speed used when HETEROGENEOUS = 0
LOGGING_LEVEL = logging.INFO  # whether to print the detail information during simulation

# routing protocol selector: "dsdv", "greedy", "mc_greedy", "macg", "qfanet", "qgeo" or "cr_qgeo"
ROUTING_PROTOCOL = "mc_greedy"  # keep "dsdv" as default so existing simulator behavior does not silently change

# ------------------ MC-Greedy routing parameters ------------------ #
MC_GREEDY_PROGRESS_WEIGHT = 0.50  # alpha: weight of geographic progress
MC_GREEDY_STABILITY_WEIGHT = 0.30  # beta: weight of predicted mobility/link stability
MC_GREEDY_CONGESTION_WEIGHT = 0.20  # gamma: weight of neighbor queue congestion
MC_GREEDY_PREDICTION_TIME = 0.50  # seconds, look-ahead horizon for link-stability prediction

# ------------------ MACG routing parameters ------------------ #
# Mobility similarity weights (must sum to 1)
MACG_POSITION_WEIGHT = 0.40
MACG_VELOCITY_WEIGHT = 0.60

# Normalization constant for velocity-similarity; expressed relative to the configured baseline
# drone speed since the simulator has no single global "max speed" constant available for the
# heterogeneous case. Purely a normalization constant for S_velocity, clamped to [0, 1] afterward.
MACG_MAX_VELOCITY_DIFFERENCE = 2 * DRONE_SPEED

# Timing (in us, following repository convention)
MACG_HELLO_INTERVAL = 0.5 * 1e6
MACG_BOOTSTRAP_DELAY = 1.0 * 1e6
MACG_NOMINATION_WINDOW = 0.25 * 1e6
MACG_CH_DECLARATION_WINDOW = 0.25 * 1e6
MACG_JOIN_WINDOW = 0.50 * 1e6

MACG_NOMINATION_THRESHOLD = 2

MACG_MAINTENANCE_INTERVAL = 1.0 * 1e6
MACG_MEMBER_MISS_LIMIT = 2
MACG_CH_MISS_LIMIT = 2

MACG_VISITED_CLUSTER_LIMIT = 8

# MACG control packet framing (Hello reuses HELLO_PACKET_LENGTH, following the convention already
# used by Greedy/MC-Greedy/DSDV hello packets)
MACG_CONTROL_PAYLOAD_LENGTH = 512  # bit
# NOTE: MACG_CONTROL_PACKET_LENGTH itself is defined further below (see "packet parameters" /
# "physical layer" section) since it depends on IP_HEADER_LENGTH, MAC_HEADER_LENGTH and
# PHY_HEADER_LENGTH, which are only defined later in this file.
# MACG_CONTROL_PACKET_LENGTH = IP_HEADER_LENGTH + MAC_HEADER_LENGTH + PHY_HEADER_LENGTH + MACG_CONTROL_PAYLOAD_LENGTH

# ------------------ CR-QGeo routing parameters ------------------ #
CR_QGEO_CONGESTION_WEIGHT = 0.40  # weight of queue congestion penalty in the intermediate reward
CR_QGEO_GAMMA_MIN = 0.30  # discount factor lower bound (stability == 0)
CR_QGEO_GAMMA_MAX = 0.90  # discount factor upper bound (stability == 1)

# ---------- hardware parameters of drone (rotary-wing) -----------#
PROFILE_DRAG_COEFFICIENT = 0.012
AIR_DENSITY = 1.225  # kg/m^3
ROTOR_SOLIDITY = 0.05  # defined as the ratio of the total blade area to disc area
ROTOR_DISC_AREA = 0.79  # m^2
BLADE_ANGULAR_VELOCITY = 400  # radians/second
ROTOR_RADIUS = 0.5  # m
INCREMENTAL_CORRECTION_FACTOR = 0.1
AIRCRAFT_WEIGHT = 100  # Newton
ROTOR_BLADE_TIP_SPEED = 500
MEAN_ROTOR_VELOCITY = 7.2  # mean rotor induced velocity in hover
FUSELAGE_DRAG_RATIO = 0.3
INITIAL_ENERGY = 200 * 1e3  # in joule; sized to survive ~3 min of flight at default speed before ENERGY_THRESHOLD
ENERGY_THRESHOLD = 2000  # in joule
MAX_QUEUE_SIZE = 200  # maximum size of drone's queue

# ----------------------- radio parameters ----------------------- #
TRANSMITTING_POWER = 0.1  # in Watt
LIGHT_SPEED = 3 * 1e8  # light speed (m/s)
CARRIER_FREQUENCY = IEEE_802_11['carrier_frequency']  # carrier frequency (Hz)
NOISE_POWER = 4 * 1e-11  # noise power (Watt)
RADIO_SWITCHING_TIME = 100  # us, the switching time of the transceiver mode
SNR_THRESHOLD = IEEE_802_11['snr_threshold']

# ---------------------- packet parameters ----------------------- #
VARIABLE_PAYLOAD_LENGTH = 0  # whether to consider random payload length of data packet
AVERAGE_PAYLOAD_LENGTH = 1024 * 8  # in bit, 1024 bytes
MAXIMUM_PAYLOAD_VARIATION = 1600  # in bit
MAX_TTL = NUMBER_OF_DRONES + 1  # maximum time-to-live value
PACKET_LIFETIME = 10 * 1e6  # 10s
IP_HEADER_LENGTH = 20 * 8  # header length in network layer, 20 byte
MAC_HEADER_LENGTH = 14 * 8  # header length in mac layer, 14 byte

# ---------------------- physical layer -------------------------- #
PATH_LOSS_EXPONENT = 2  # for large-scale fading
PLCP_PREAMBLE = 128 + 16  # including synchronization and SFD (start frame delimiter)
PLCP_HEADER = 8 + 8 + 16 + 16  # including signal, service, length and HEC (header error check)
PHY_HEADER_LENGTH = PLCP_PREAMBLE + PLCP_HEADER  # header length in physical layer, PLCP preamble + PLCP header

ACK_HEADER_LENGTH = 16 * 8  # header length of ACK packet, 16 byte
ACK_PACKET_LENGTH = ACK_HEADER_LENGTH + 14 * 8  # bit

HELLO_PACKET_PAYLOAD_LENGTH = 256  # bit
HELLO_PACKET_LENGTH = IP_HEADER_LENGTH + MAC_HEADER_LENGTH + PHY_HEADER_LENGTH + HELLO_PACKET_PAYLOAD_LENGTH

# MACG control packet length (NOMINATION / CH_DECLARE / JOIN_REQUEST / JOIN_ACCEPT / CLUSTER_STATE /
# MAINTENANCE / MAINT_RESPONSE / GATEWAY_UPDATE all share this framing; MACG Hello reuses
# HELLO_PACKET_LENGTH above, following the convention already used by Greedy/MC-Greedy/DSDV)
MACG_CONTROL_PACKET_LENGTH = IP_HEADER_LENGTH + MAC_HEADER_LENGTH + PHY_HEADER_LENGTH + MACG_CONTROL_PAYLOAD_LENGTH

# define the range of "id" of different types of packets
"""
|--------------|--------------|--------------|--------------|--------------|--------------|--------------|--------------|
0            10000          20000          30000          40000          50000          60000          70000
|   data pkt   |   hello pkt  |    ack pkt   |    vf pkt    |   grad msg   |    rts pkt   |    cts pkt   | macg ctl pkt |
"""
GL_ID_DATA_PACKET = 0
GL_ID_HELLO_PACKET = 10000
GL_ID_ACK_PACKET = 20000
GL_ID_VF_PACKET = 30000
GL_ID_GRAD_MESSAGE = 40000
GL_ID_RTS_PACKET = 50000
GL_ID_CTS_PACKET = 60000
GL_ID_MACG_CONTROL_PACKET = 70000

# ------------------ physical layer parameters ------------------- #
BIT_RATE = IEEE_802_11['bit_rate']
BIT_TRANSMISSION_TIME = 1/BIT_RATE * 1e6
BANDWIDTH = IEEE_802_11['bandwidth']
SENSING_RANGE = 750  # in meter, defines the area where a sending node can disturb a transmission from a third node

# --------------------- mac layer parameters --------------------- #
SLOT_DURATION = IEEE_802_11['slot_duration']
SIFS_DURATION = IEEE_802_11['SIFS']
DIFS_DURATION = SIFS_DURATION + (2 * SLOT_DURATION)
CW_MIN = 31  # initial contention window size
ACK_TIMEOUT = ACK_PACKET_LENGTH / BIT_RATE * 1e6 + SIFS_DURATION + 50  # maximum waiting time for ACK, in us
MAX_RETRANSMISSION_ATTEMPT = 5

# whether to perform an RTS/CTS handshake before a unicast data transmission, to mitigate the hidden-terminal
# problem (a sender and a receiver may each be unable to sense the other's neighbors)
ENABLE_RTS_CTS = True

RTS_HEADER_LENGTH = 16 * 8  # header length of RTS packet, 16 byte
RTS_PACKET_LENGTH = RTS_HEADER_LENGTH + 6 * 8  # bit

CTS_HEADER_LENGTH = 16 * 8  # header length of CTS packet, 16 byte
CTS_PACKET_LENGTH = CTS_HEADER_LENGTH + 6 * 8  # bit

CTS_TIMEOUT = CTS_PACKET_LENGTH / BIT_RATE * 1e6 + SIFS_DURATION + 50  # maximum waiting time for CTS, in us
