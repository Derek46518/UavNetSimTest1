from utils.util_function import euclidean_distance_3d
from utils import config

class SphericalObstacle:
    def __init__(self, center, radius, obstacle_id=1):
        self.center = center  # in meter
        self.radius = radius  # in meter
        self.id = obstacle_id

    def add_to_grid(self, grid):
        x0, y0, z0 = self.center
        x0, y0, z0 = int(round(x0)), int(round(y0)), int(round(z0))

        for x in range(max(0, x0 - self.radius), min(config.MAP_LENGTH, x0 + self.radius)):
            for y in range(max(0, y0 - self.radius), min(config.MAP_WIDTH, y0 + self.radius)):
                for z in range(max(0, z0 - self.radius), min(config.MAP_HEIGHT, z0 + self.radius)):
                    if euclidean_distance_3d([x, y, z], self.center) <= self.radius:
                        grid[int(x / config.GRID_RESOLUTION),
                             int(y / config.GRID_RESOLUTION),
                             int(z / config.GRID_RESOLUTION)] = self.id


class CubeObstacle:
    def __init__(self, center, length, width, height, obstacle_id=2):
        self.center = center
        self.length = length
        self.width = width
        self.height = height
        self.id = obstacle_id

    def add_to_grid(self, grid):
        x0, y0, z0 = self.center
        x0, y0, z0 = int(round(x0)), int(round(y0)), int(round(z0))

        for x in range(max(0, x0 - int(self.length / 2)), min(config.MAP_LENGTH, x0 + int(self.length / 2))):
            for y in range(max(0, y0 - int(self.width / 2)), min(config.MAP_WIDTH, y0 + int(self.width / 2))):
                for z in range(max(0, z0 - int(self.height / 2)), min(config.MAP_HEIGHT, z0 + int(self.height / 2))):
                    grid[int(x / config.GRID_RESOLUTION),
                         int(y / config.GRID_RESOLUTION),
                         int(z / config.GRID_RESOLUTION)] = self.id
