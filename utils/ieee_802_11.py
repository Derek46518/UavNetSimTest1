class IeeeStandard:
    def __init__(self):
        # IEEE 802.11a
        """
        Several notes about IEEE 802.11a:

        - The relationship between different bit rates and SNR threshold:
        |--------------|-------------------|-----------------|
        |   Bit rate   |  Modulation mode  |  SNR threshold  |
        |   6 Mbps     |      BPSK         |      4 dB       |
        |   9 Mbps     |      BPSK         |      5.5 dB     |
        |   12 Mbps    |      QPSK         |      7 dB       |
        |   18 Mbps    |      QPSK         |      8.5 dB     |
        |   24 Mbps    |      16-QAM       |      12 dB      |
        |   36 Mbps    |      16-QAM       |      16 dB      |
        |   48 Mbps    |      64-QAM       |      19.5 dB    |
        |   54 Mbps    |      64-QAM       |      21 dB      |
        """

        self.a_802_11 = {'mode': 'IEEE_802_11a',
            'carrier_frequency': 5 * 1e9,  # 5 GHz
            'bit_rate': 54 * 1e6,  # 54 Mbps
            'bandwidth': 20 * 1e6,  # 20 MHz
            'slot_duration': 9,  # microseconds
            'SIFS': 16,
            'snr_threshold': 21}

        # IEEE 802.11b
        """
        Several notes about IEEE 802.11b:
        - Spectrum partitioning (one can find illustration in 'img' folder):
          - The IEEE 802.11b standard operates in the 2.4G band, with a frequency range of 2.400-2.4835 GHz and a 
            total bandwidth of 83.5 MHz
          - There are total 14 channels, where channel 1, 6, 11 are orthogonal
          - The bandwidth of each sub-channel is 22 MHz
          - The available channels mentioned above are defined with 5 MHz separation between consecutive carries
          - There is frequency band overlap between multiple adjacent sub-channels 
          - DSSS (Direct Sequence Spread Spectrum) is most commonly used in IEEE 802.11, once spread, the resulting
            signal occupies a bandwidth of about 20 MHz, which is sightly lower than the bandwidth of a sub-channel
          - In 2.4 GHz band, only three sub-channels (1, 6 and 11) are non-overlapping.
        
        - The relationship between different bit rates and SNR threshold:
        |--------------|-------------------|-----------------|
        |   Bit rate   |  Modulation mode  |  SNR threshold  |
        |    1 Mbps    |       DBPSK       |       4 dB      |
        |    2 Mbps    |       DQPSK       |       6 dB      |
        |   5.5 Mbps   |        CCK        |       8 dB      |
        |   11 Mbps    |        CCK        |     10-12 dB    |
          
        Packet structure at physical layer in 802.11b
        |---------------|-------------|---------------------------------------------------|
        | PLCP preamble | PLCP header |                MPDU at MAC layer                  | 
                ↑              ↑                               ↑
              DBPSK     DBPSK or DQPSK    DBPSK or DQPSK or CCK 5.5 Mbps or CCK 11 Mbps
        
        Reference:
        [1] Villegas. E. G, Lopez-Aguilera. E, Vidal. R, Paradells. J, "Effect of Adjacent-channel Interference in IEEE 
            802.11 WLANs," in 2007 2nd international conference on cognitive radio oriented wireless networks and 
            communications, 2007, pp. 118-125.
        
        """
        self.b_802_11 = {'mode': 'IEEE_802_11b',
            'carrier_frequency': 2.4 * 1e9,
            'bit_rate': 2 * 1e6,  # up to 11 Mbps
            'bandwidth': 22 * 1e6,  # 22 MHz
            'slot_duration': 20,  # microseconds
            'SIFS': 10,
            'snr_threshold': 6}

        # IEEE 802.11g

        """
        Several notes about IEEE 802.11b:
        
        - The relationship between different bit rates and SNR threshold:
        |--------------|-------------------|-----------------|
        |   Bit rate   |  Modulation mode  |  SNR threshold  |
        |   6 Mbps     |      BPSK         |      4 dB       |
        |   9 Mbps     |      BPSK         |      5.5 dB     |
        |   12 Mbps    |      QPSK         |      7 dB       |
        |   18 Mbps    |      QPSK         |      8.5 dB     |
        |   24 Mbps    |      16-QAM       |      12 dB      |
        |   36 Mbps    |      16-QAM       |      16 dB      |
        |   48 Mbps    |      64-QAM       |      19.5 dB    |
        |   54 Mbps    |      64-QAM       |      21 dB      |
        """

        self.g_802_11 = {'mode': 'IEEE_802_11g',
            'carrier_frequency': 2.4 * 1e9,  # 2.4 GHz
            'bit_rate': 54 * 1e6,  # 54 Mbps
            'bandwidth': 20 * 1e6,  # 20 MHz
            'slot_duration': 9,  # microseconds
            'SIFS': 10,
            'snr_threshold': 21}
