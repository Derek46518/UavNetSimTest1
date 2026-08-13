from collections import defaultdict
from routing.base.base_table import BaseTable


class GradCostTable(BaseTable):
    """
    Cost table of GRAd (Gradient Routing in ad hoc networks) (v1.0)

    Type of the cost table: dictionary
    the format of the cost table is:
    {target_id 1: [seq_#, est_cost1, updated time1], target_id 2: [seq_#, est_cost2, updated time2],...}
    Explanation:
    1) "target_id": is the identifier of a remote drone to which this cost entry refers
    2) "seq_#": the highest sequence number received so far in a message from "target_id". When compared against the
        seq_# of a newly arrived message, this field discriminates between a new message and a copy of a previously
        received message
    3) "est_cost": the most recent and best estimated cost (number of hops in this version) for delivering a message
        to "target_id"
    4) "updated time": this field is used to determine if the entry is expired

    The cost table can answer two question:
    1) "Is this message a copy of a previously received message?" This is determined by comparing the sequence number
        in the incoming message against the last sequence number recorded in the cost table
    2) "What is the estimated cost of sending a message to a certain target drone?" In cost table, each "target_id" is
        associated with "est_cost"

    References:
        [1] Poor R. Gradient routing in ad hoc networks[J]. 2000.

    Author: Zihao Zhou, eezihaozhou@gmail.com
    Created at: 2024/4/20
    Updated at: 2026/3/10
    """

    def __init__(self, env, my_drone):
        super().__init__(env, my_drone)
        self.env = env
        self.my_drone = my_drone

    # get the estimated cost for "target_id"
    def get_est_cost(self, target_id):
        if target_id not in self.table.keys():
            raise RuntimeError('This item is not in the cost table')
        else:
            return self.table[target_id][1]

    # update entry, core function
    def update_entry(self, grad_message, cur_time):
        originator_id = grad_message.originator.identifier  # remote drone
        seq_num = grad_message.seq_num
        accrued_cost = grad_message.accrued_cost

        if originator_id is not self.my_drone.identifier:
            if originator_id not in self.table.keys():  # no matching entry is found
                self.table[originator_id] = [seq_num, accrued_cost, cur_time]  # create a new entry
            elif self.table[originator_id][0] < seq_num:  # incoming message is fresher
                self.table[originator_id] = [seq_num, accrued_cost, cur_time]  # entry is updated
            elif accrued_cost < self.table[originator_id][1]:
                self.table[originator_id][1] = accrued_cost
                self.table[originator_id][2] = cur_time
        else:
            pass

    # used to determine if it has a route for delivering a data packet
    def has_entry(self, target_id):
        has_route = False
        if target_id in self.table.keys():
            has_route = True

        return has_route

    def print_item(self, my_drone):
        print('|----------Neighbor Table of: ', my_drone.identifier, ' ----------|')
        for key in self.table.keys():
            print('Target_id: ', key, ', seq_#: ', self.table[key][0], ', est_cost: ', self.table[key][1],
                  ', updated time is: ', self.table[key][2])
        print('|-----------------------------------------------------------------|')
