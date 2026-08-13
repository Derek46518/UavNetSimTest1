from queue import PriorityQueue
from utils import config
from utils.util_function import euclidean_distance_3d


"""
Drone 3D path planning using A* algorithm

NOTE: if the distance between the starting point and the end point is too long, then the grid resolution
should be set large to shorten the running time

References:
[1] https://www.redblobgames.com/pathfinding/a-star/introduction.html
[2] https://github.com/yy1115/A-algorithm-3D-path-planning/

Author: Zihao Zhou, eezihaozhou@gmail.com
Created at: 2025/7/8
"""

def get_valid_neighbor_pos(current_pos, grid):
    re = config.GRID_RESOLUTION

    neighbors = []
    x, y, z = current_pos[0], current_pos[1], current_pos[2]

    directions = [
        (-re, 0, 0), (re, 0, 0),
        (0, -re, 0), (0, re, 0),
        (0, 0, -re), (0, 0, re),
        (-re, -re, 0), (-re, re, 0),
        (re, -re, 0), (re, re, 0),
        (-re, 0, -re), (-re, 0, re),
        (re, 0, -re), (re, 0, re),
        (0, -re, -re), (0, -re, re),
        (0, re, -re), (0, re, re),
        (-re, -re, -re), (-re, -re, re),
        (-re, re, -re), (-re, re, re),
        (re, -re, -re), (re, -re, re),
        (re, re, -re), (re, re, re)
    ]

    for dx, dy, dz in directions:
        next_x = x + dx
        next_y = y + dy
        next_z = z + dz
        if 0 <= next_x < config.MAP_LENGTH and 0 <= next_y < config.MAP_WIDTH and 0 <= next_z < config.MAP_HEIGHT:
            if grid[int(next_x/config.GRID_RESOLUTION),
                    int(next_y/config.GRID_RESOLUTION),
                    int(next_z/config.GRID_RESOLUTION)] == 0:
                neighbors.append((next_x, next_y, next_z))

    return neighbors


def a_star_3d(start_pos, end_pos, grid):
    """
    Implementation of the A* algorithm for 3D path planning

    Args:
        start_pos: starting position of the drone, tuple(list)
        end_pos: ending position of the drone, tuple(list)
        grid: the 3D mesh

    Returns: the path (if it exists)

    """

    # error check
    # 1. boundary check
    boundary = tuple([config.MAP_LENGTH, config.MAP_WIDTH, config.MAP_HEIGHT])
    if not all(0 <= s < b for s, b in zip(start_pos, boundary)):
        raise ValueError(f"The starting point is outside the boundary of the map!")
    elif not all(0 <= e < b for e, b in zip(end_pos, boundary)):
        raise ValueError(f"The end point is outside the boundary of the map!")

    # 2. resolution check
    if not all(s % config.GRID_RESOLUTION == 0 for s in start_pos):
        raise ValueError(f"It is recommended that the coordinate value of the starting point be set as integer "
                         f"multiples of the grid resolution!")
    elif not all(e % config.GRID_RESOLUTION == 0 for e in end_pos):
        raise ValueError(f"It is recommended that the coordinate value of the end point be set as integer "
                         f"multiples of the grid resolution!")

    # 3. Obstacle check
    if grid[int(start_pos[0] / config.GRID_RESOLUTION),
            int(start_pos[1] / config.GRID_RESOLUTION),
            int(start_pos[2] / config.GRID_RESOLUTION)] != 0:
        raise ValueError(f"The starting point collides with the obstacle!")
    elif grid[int(end_pos[0] / config.GRID_RESOLUTION),
              int(end_pos[1] / config.GRID_RESOLUTION),
              int(end_pos[2] / config.GRID_RESOLUTION)] != 0:
        raise ValueError(f"The end point collides with the obstacle!")

    frontier = PriorityQueue()  # used to store the points to be traversed
    frontier.put((0, start_pos))
    came_from = dict()
    came_from[start_pos] = None

    cost_so_far = dict()
    cost_so_far[start_pos] = 0

    while not frontier.empty():
        _, current_pos = frontier.get()

        if current_pos == end_pos:
            current_pos = end_pos
            path = []
            while current_pos != start_pos:
                path.append(current_pos)
                current_pos = came_from[current_pos]
            path.append(start_pos)
            path.reverse()
            return path

        for neighbor_pos in get_valid_neighbor_pos(current_pos, grid):
            new_cost = cost_so_far[current_pos] + euclidean_distance_3d(current_pos, neighbor_pos)

            if neighbor_pos not in cost_so_far or new_cost < cost_so_far[neighbor_pos]:
                cost_so_far[neighbor_pos] = new_cost
                priority = new_cost + euclidean_distance_3d(neighbor_pos, end_pos)
                frontier.put((priority, neighbor_pos))
                came_from[neighbor_pos] = current_pos

    return None
