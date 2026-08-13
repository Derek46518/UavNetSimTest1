from simulator.log import logger
from routing.base.base_table import BaseTable


class DsdvRoutingTable(BaseTable):
    """
    Routing table of DSDV (Destination-Sequenced Distance Vector)

    Type of the routing table: dictionary
    The structure of the routing table is:
    {dst1: [next hop, metric (hop count), seq_num of dst1, updated time1],
     dst2: [next hop, metric (hop count), seq_num of dst2, updated time2],
     ...}

    Attributes:
        env: simulation environment
        my_drone: the drone that keeps this routing table

    References:
        [1] Perkins, C. E., and Bhagwat, P.,"Highly dynamic destination-sequenced distance-vector routing (DSDV) for
            mobile computer," ACM SIGCOMM computer communication review, vol. 24, no. 4, pp. 234-244, 1994.
        [2] He. G, "Destination-sequenced distance vector (DSDV) protocol," Networking Laboratory, Helsinki University
            of Technology, 135, pp. 1-9, 2002.

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/4/14
    Updated at: 2026/3/10
    """

    def __init__(self, env, my_drone):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone

        # Initialize the routing table, sequence number if even number
        self.table[self.my_drone.identifier] = [self.my_drone.identifier, 0, self.my_drone.identifier*2, self.env.now]

    # Update item according to the receiving packet
    def update_item(self, packet, cur_time):
        src_drone = packet.src_drone
        if src_drone is not self.my_drone:  # the hello packet is not broadcast by myself
            for dst_id in packet.routing_table.keys():
                metric = packet.routing_table[dst_id][1]
                seq_num = packet.routing_table[dst_id][2]
                if dst_id not in self.table.keys():
                    self.table[dst_id] = [src_drone.identifier, metric+1, seq_num, cur_time]
                elif seq_num > self.table[dst_id][2]:
                    self.table[dst_id] = [src_drone.identifier, metric+1, seq_num, cur_time]
                elif seq_num == self.table[dst_id][2]:
                    if metric < self.table[dst_id][1]:
                        self.table[dst_id] = [src_drone.identifier, metric+1, seq_num, cur_time]
                else:
                    pass

    # Remove the expired item
    def purge(self):
        flag = 0
        if not bool(self.table):
            # it means that the neighbor table is empty
            return flag

        for key in list(self.table):
            if key is not self.my_drone.identifier:
                updated_time = self.get_updated_time(key)
                if updated_time + self.entry_life_time < self.env.now:
                    expired_next_hop = self.table[key][0]  # expired next hop

                    # all entries through this next hop should be set to invalid
                    for key2 in list(self.table):
                        if self.table[key2][0] == expired_next_hop:
                            self.table[key2][1] = float('inf')
                            self.table[key2][2] += 1
                            self.table[key2][3] = self.env.now

                    flag = 1  # broken links have occurred

        return flag

    # Determine if it has the valid item to certain destination
    def has_entry(self, dst_id):
        if dst_id not in self.table.keys():
            next_hop_id = self.my_drone.identifier
        elif self.table[dst_id][1] != float('inf'):
            # get the next hop to the destination
            next_hop_id = self.table[dst_id][0]
        else:
            next_hop_id = self.my_drone.identifier

        return next_hop_id

    def print_item(self, my_drone):
        logger.info('|----------Routing Table of: %s ----------|', my_drone.identifier)
        for key in self.table.keys():
            logger.info('Dst_id: %s, next hop is: %s, metric is: %s, seq_num (dst_id) is: %s, updated time is: %s',
                         key, self.table[key][0], self.table[key][1], self.table[key][2],
                         self.table[key][3])
        logger.info('|-----------------------------------------------------------------|')
