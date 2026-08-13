import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from utils import config
from utils.util_function import euclidean_distance_3d
from phy.large_scale_fading import maximum_communication_range


def scatter_plot(simulator):
    """Draw a static scatter plot, includes communication edges (without obstacles)"""

    fig = plt.figure()
    ax = fig.add_axes(Axes3D(fig))

    for drone1 in simulator.drones:
        for drone2 in simulator.drones:
            if drone1.identifier != drone2.identifier:
                ax.scatter(drone1.coords[0], drone1.coords[1], drone1.coords[2], c='red', s=30)
                distance = euclidean_distance_3d(drone1.coords, drone2.coords)
                if distance <= maximum_communication_range():
                    x = [drone1.coords[0], drone2.coords[0]]
                    y = [drone1.coords[1], drone2.coords[1]]
                    z = [drone1.coords[2], drone2.coords[2]]
                    ax.plot(x, y, z, color='black', linestyle='dashed', linewidth=1)

    ax.set_xlim(0, config.MAP_LENGTH)
    ax.set_ylim(0, config.MAP_WIDTH)
    ax.set_zlim(0, config.MAP_HEIGHT)

    # maintain the proportion of the x, y and z axes
    ax.set_box_aspect([config.MAP_LENGTH, config.MAP_WIDTH, config.MAP_HEIGHT])

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')

    plt.show()

def scatter_plot_with_obstacles(simulator, grid, path_list):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for obst_type in simulator.obstacle_type:
        obstacle_points = np.argwhere(grid == obst_type)
        if obstacle_points.size > 0:
            ax.scatter(obstacle_points[:, 0] * config.GRID_RESOLUTION,
                       obstacle_points[:, 1] * config.GRID_RESOLUTION,
                       obstacle_points[:, 2] * config.GRID_RESOLUTION)

    for path in path_list:
        if path:
            path = np.array(path)
            ax.plot(path[:, 0], path[:, 1], path[:, 2], color='blue', linewidth=3)

    ax.set_xlim(0, config.MAP_LENGTH)
    ax.set_ylim(0, config.MAP_WIDTH)
    ax.set_zlim(0, config.MAP_HEIGHT)

    # maintain the proportion of the x, y and z axes
    ax.set_box_aspect([config.MAP_LENGTH, config.MAP_WIDTH, config.MAP_HEIGHT])

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')

    plt.show()
