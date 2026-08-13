<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/logo.png" width="650px">
</div>

<div align="center">
  <h1>UavNetSim: 基于Python的无人机通信网络仿真平台</h1>

  <img src="https://img.shields.io/badge/Github-%40Zihao--Felix--Zhou-blue" height="20">
  <img src="https://img.shields.io/badge/License-MIT-brightgreen" height="20">
  <img src="https://img.shields.io/badge/Version-V1.0-orange" height="20">
  <img src="https://img.shields.io/badge/Contributions-Welcome-yellowgreen" height="20">
  <a href="https://hellogithub.com/repository/Zihao-Felix-Zhou/UavNetSim-v1" target="_blank"><img src="https://abroad.hellogithub.com/v1/widgets/recommend.svg?rid=51f926ec044046afb3ed23a912421445&claim_uid=yc7sS80jimthluU&theme=small" alt="Featured｜HelloGitHub" /></a>
 

  <h3>让仿真对新手更友好! </h3>
</div>

以其他语言阅读此文档: [English](README.md)  

这一款基于Python的仿真平台能够对无人机网络中的多个组件进行真实且完整的建模，包括网络层、媒体接入控制层、物理层，以及无人机移动模型和能量模型。此外，该平台极易扩展，便于用户定制及开发不同的协议以适应不同的应用需求。 <br>

该项目对应于下方所示的论文，除此之外，我们近期也新增了许多新的模块以及baselines。<br>

> **[UavNetSim-v1: A Python-based Simulation Platform for UAV Communication Networks](https://arxiv.org/abs/2507.09852)** <br>
> [Zihao Zhou](https://zihao-felix-zhou.github.io/)<sup>1</sup>, [Zipeng Dai](http://zipengdai.com/)<sup>2</sup>, Linyi Huang<sup>3</sup>, [Cui Yang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=YBh67JO2Lu3MRcgZBW!y0g==)<sup>1</sup>, [Youjun Xiang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=OqvoZ7Uc98hlRMLm8c2JGA==)<sup>1</sup>, [Jie Tang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=jAxeXRUecjTAjkxrmc2Dnw==)<sup>1</sup> and [Kai-kit Wong](https://www.ee.ucl.ac.uk/~uceekwo/)<sup>4,5</sup> <br>
> <sup>1</sup> School of Electronic and Information Engineering, South China University of Technology <br>
> <sup>2</sup> Department of Computer Science and Technology, Beijing Institute of Technology <br>
> <sup>3</sup> Thrust of ROAS, The Hong Kong University of Science and Technology (Guangzhou) <br>
> <sup>4</sup> Department of Electrical and Electronic Engineering, University College London <br>
> <sup>5</sup> Yonsei Frontier Lab, Yonsei University

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/Schematic_of_uav_swarms.png" width="1000px">
</div>

## 依赖
- matplotlib==3.10.1
- numpy==2.2.4
- openpyxl==3.1.5
- Pillow==11.2.1
- scikit_opt==0.6.6
- simpy==4.1.1

## 特色
在开始您的仿真之旅前，我们建议您先阅读本小节，本节中介绍了该平台的一些特点，您可以据此来判断该平台是否满足您的开发或研究需求。
- 该平台完全基于Python开发（主要是基于Python中的SimPy库）；
- 更加适合对**路由协议**、**MAC协议**以及**移动控制算法**（如：**拓扑控制**、**轨迹优化**）的开发与验证。未来我们希望能够进一步扩展该平台以支持更多不同层的算法与协议；
- 支持**强化学习**以及其他基于AI的算法；
- 易于扩展（1.采用**模块化编程方案**，因此用户可以很轻易地增加自己设计的模块；2. 潜在地支持不同的应用场景，如**飞行自组织网络**，**无人机辅助的数据采集**，**空地一体化网络**等）；
- **较好的可视化**，该平台能够直观地展示无人机的**飞行轨迹**以及**包的传输路径**，这能够帮助用户直观地分析协议的行为；
- 如果您从事无人机辅助的无线通信系统，并希望能够考虑更多**跨层指标**（如端到端时延、包传输率，吞吐量等），那么这款平台将会适合你！

## 项目架构

```
.
├── README.md
├── allocation
│   ├── central_controller.py
│   └── channel_assignment.py
├── energy
│   └── energy_model.py
├── entities
│   ├── drone.py
│   ├── obstacle.py
│   └── packet.py
├── mac
│   ├── csma_ca.py
│   └── pure_aloha.py
├── mobility
│   ├── gauss_markov_3d.py
│   ├── random_walk_3d.py
│   ├── random_waypoint_3d.py
│   └── start_coords.py
├── path_planning
│   ├── astar
│   │   └── astar.py
├── phy
│   ├── channel.py
│   ├── large_scale_fading.py
│   └── phy.py
├── routing
│   ├── dsdv
│   │   ├── dsdv.py
│   │   ├── dsdv_packet.py
│   │   └── dsdv_routing_table.py
│   ├── grad
│   │   └── ...
│   ├── greedy
│   │   └── ...
│   ├── opar
│   │   └── ...
│   └── q_routing
│       └── ...
├── simulator
│   ├── metrics.py
│   └── simulator.py
├── topology
│   └── virtual_force
│       ├── vf_motion_control.py
│       ├── vf_neighbor_table.py
│       └── vf_packet.py
├── utils
│   ├── config.py
│   ├── ieee_802_11.py
│   └── util_function.py
├── visualization
│   ├── static_drawing.py
│   └── visualizer.py
└── main.py
```
该项目的入口是```main.py```文件，我们甚至可以直接一键运行来提前预览一下效果，但我们还是建议您先阅读本节，了解该仿真平台的模块组成和相应的功能。

- ```allocation```:该文件夹中包括了不同的资源分配算法模块，例如：子信道分配策略。未来可以考虑进一步实现功率分配算法。
- ```energy```: 该文件夹中包括了无人机的能量消耗模型，包括飞行以及通信相关的能量消耗。
- ```entities```: 它包含与仿真中涉及的主要实体相对应的所有模块。
- ```mac```: 其包含了不同媒体接入控制协议的实现。
- ```mobility```: 其包含了不同的无人机三维移动模型。
- ```path_planning```: 其包含了不同的无人机三维路径规划算法模块（如A*算法）。
- ```phy```: 其主要包括了物理层无线信道的建模，以及对单播、多播和广播行为的定义。
- ```routing```: 其主要包括了不同路由协议的实现。
- ```simulator```: 其包含了进行仿真和评估网络性能指标所需的所有类。
- ```topology```: 其包含了不同的无人机集群拓扑控制算法的实现。
- ```utils```: 其包含了关键的仿真参数设置以及一些常用的函数。
- ```visualization```: 能够提供无人机节点分布、飞行轨迹和数据包转发路径的可视化展示。

| 层 | 当前已经实现的协议、算法或模型 |
| --- | --- |
| 应用层 | 服从均匀分布的数据包达到 <br> 服从泊松分布的数据包到达 |
| 传输层 | Automatic repeat request (ARQ) |
| 网络层 | 路由协议: <br> <ul><li>[DSDV: Destination-Sequenced Distance-Vector routing](https://dl.acm.org/doi/abs/10.1145/190809.190336)</li> <li>[GRAd: Gradient Routing in Ad Hoc Networks](www.media.mit.edu/pia/Research/ESP/texts/poorieeepaper.pdf)</li> <li>[Greedy forwarding](https://en.wikipedia.org/wiki/Geographic_routing)</li> <li>[OPAR: Optimized Predictive and Adaptive Routing](https://ieeexplore.ieee.org/abstract/document/9484489)</li> <li>[Q-FANET: Improved Q-learning based Routing Protocol for FANETs](https://www.sciencedirect.com/science/article/abs/pii/S1389128621003595)</li> <li>[QMR: Q-learning based Multi-objective optimization Routing](https://hal.science/hal-02970649v1/document)</li> <li>[QGeo: Q-learning-based Geographic routing](https://ieeexplore.ieee.org/abstract/document/7829268/)</li> <li>[Classical Q-Routing](https://proceedings.neurips.cc/paper/1993/hash/4ea06fbc83cdd0a06020c35d50e1e89a-Abstract.html)</li></ul>|
| 拓扑控制层 | 随机移动模型: <br> <ul><li>[3D Gauss-Markov mobility model](https://repository.arizona.edu/bitstream/handle/10150/604297/ITC_2010_10-03-06.pdf?sequence=1&isAllowed=y)</li><li>[3D Random Waypoint mobility model](https://ieeexplore.ieee.org/document/8671460)</li><li>[3D Random Walk mobility model](https://link.springer.com/chapter/10.1007/978-1-4419-6050-4_3#citeas)</li></ul> 拓扑控制算法: <br> <ul><li>[Virtual force-based topology control](https://ieeexplore.ieee.org/document/5555924)</li></ul> 路径规划以及避障算法: <br> <ul><li>A* 3D path planning</li></ul>|
| 媒体接入控制层 |<ul><li>[CSMA/CA: Carrier-Sense Multiple Access with Collision Avoidance](https://en.wikipedia.org/wiki/Carrier-sense_multiple_access_with_collision_avoidance)</li> <li>[Pure ALOHA](https://www.tutorialspoint.com/data_communication_computer_network/pure_aloha.htm)</li></ul>|
| 物理层 | 所考虑的物理层特性: <br> <ul><li>视距信道</li> <li>概率视距信道</li> <li>数据包碰撞以及信号干扰</li> <li>单播、多播以及广播</li></ul> |

## 安装及使用
首先，下载该项目:
```
git clone https://github.com/Zihao-Felix-Zhou/UavNetSim-v1.git
```
运行 ```main.py``` 以启动仿真.   

## 核心逻辑
下图展示了 *UavNetSim* 平台中包传输的主要过程。无人机的buffer设置为了一个容量为1的SimPy资源，这就意味着一个无人机一次最多只能发送一个包。如果有多个包需要传输，那么它们就需要根据其到达时间来排队等待buffer资源（这属于没有考虑包优先级的情况），因此我们就可以根据这种机制来模拟排队时延。此外，我们还注意到图中有两个容器：```transmitting_queue``` 和 ```waiting_list```，对于所有由无人机自身所产生的数据包和控制包，或者是该无人机从其他节点处接收到且需要进一步转发的包，它们都会被放到```transmitting_queue```中。```feed_packet```函数会周期性（此周期是一个非常短的时间）地读取```transmitting_queue```头部的包，并令其等待 ```buffer``` 资源。需要注意的是ACK包会直接等待 ```buffer``` 资源而无需进入```transmitting_queue```。  

当一个包被读取后，首先需要判断该包的类型。如果该包是一个控制包（通常来说是以广播的形式，不需要选择下一跳），那么它将会直接开始等待```buffer```资源。如果该包是数据包，那么则需要调用路由协议来选择下一跳，如果找到了合适的下一跳节点，那么该数据包将会开始等待 ```buffer``` 资源，否则，该包将会被放入到 ```waiting_list```中，一旦该无人机在未来某个时间内重新找到了相关的路由信息，该无人机节点就会将此数据包从 ```waiting_list``` 中取出，并加入到 ```transmitting_queue```中。  

当包得到了 ```buffer``` 资源之后，MAC协议就会执行以争用（或调度）无线信道。当包成功被其他无人机接收后，同样在接收端需要判断包的类型。例如，如果收到的是数据包，那么接收方需要在一个SIFS时间后回复ACK包。除此之外，如果接收方是数据包的目的地，那么将会开始记录网络指标（如PDR,端到端时延等），否则，就意味着该数据包还需要被进一步转发，因此该数据包将会被放入到接收方的 ```transmitting_queue```中。  

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/transmitting_procedure.png" width="700px">
</div>

## 模块概述
### 路由协议
数据包路由在无人机通信网络中扮演着重要的角色, 能够帮助不同无人机节点之间实现协同. 在该项目中, 我们实现了如**贪心地理路由**, **梯度路由**, **DSDV, OPAR**, 以及一些 **基于强化学习的路由协议**. 下图展示了数据包路由的基本流程. 更多的细节可以参考对应的文献 [1]-[5].

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/routing.png" width="700px">
</div>

### 媒体接入控制协议
在该项目中，目前我们已经实现了CSMA/CA以及纯Aloha两种MAC协议。我将简要概述在这个项目中实现的版本，并重点介绍如何在这个项目中实现信号干扰和碰撞。下图展示了一个基础版CSMA/CA（不包括RTS/CTS机制）协议下数据包传输的例子。当无人机想要传输一个数据包时：  
1. 其首先需要等待直到信道空闲
2. 当信道空闲时，该无人机将会启动计时器，并等待 ```DIFS+backoff``` 段时间，其中退避时间的长短和重传次数有关
3. 如果计时器倒数至0了且都没有被打断，那么该无人机就能够占用该信道并开始发送包
4. 如果计时器在倒数过程中被打断，这意味着该无人机此轮争用信道失败。该无人机会冻结计时器，等待信道重新变为空闲，之后再重新启动计时器

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/csmaca.png" width="800px">
</div>

下图展示了在纯Aloha协议下包的传输过程。当无人机想要传输一个数据包时（如果是首次发送）：  

1. 该无人机直接发送该包，无需监听信道以及退避
2. 在发送完该数据包后，该无人机节点开始等待ACK包
3. 如果无人机顺利接收到了ACK包，则 ```mac_send``` 过程就会结束
4. 如果没有收到ACK包，则该无人机将会根据重传次数随机等待一段时间，之后再重新发送该数据包

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/pure_aloha.png" width="800px">
</div>

从上图中，我们可以看到，不仅仅是两个无人机同时发送数据包会导致数据包冲突，如果两个数据包的传输时间出现重叠，也意味着发生了碰撞。因此，在我们的项目中，每个无人机每隔很短的时间就会检查它的inbox，并有几件重要的事情要做（如下图所示）：  

1. 删除其inbox中与当前时间距离大于最大包传输延迟两倍的包记录。这减少了计算开销，因为保证这些包已经处理过，不会干扰尚未处理的包
2. 检查inbox中的包记录，看看哪个包已经完整地传输给了自己
3. 如果存在这样的记录，则在所有无人机的inbox记录中找到与该数据包在传输时间上重叠的其他数据包，并l利用它们计算SINR

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/reception_logic.png" width="800px">
</div>

## 移动模型
移动模型是更加真实地展示无人机网络特性的最重要的模块之一。在该项目中，我们目前实现了三种随机移动模型，包括： **3D 高斯马尔可夫移动模型**, **3D 随机游走移动模型** 以及**3D 随机航点移动模型**。具体而言，在离散时间的仿真中要想实现无人机节点的连续运动是比较难的，因此我们设置了一个 ```position_update_interval``` 来周期性地更新无人机的位置，我们就假设无人机在这个较小的时间间隔内是连续运动的。```position_update_interval```越小，对应的仿真精度就更高，但也会相应地增大仿真的时间。在三种移动模型下仿真单架无人机100s内的轨迹如下图所示：  

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/mobility_model.png" width="700px">
</div>

## 3D路径规划
我们的UavNetSim-v1平台现已支持对无人机三维路径规划算法的设计与测试。目前我们所实现的baseline是A*算法，后续我们也将会持续增加更多的baseline，例如Dijkstra, DFS, BFS以及一些基于深度强化学习的路径规划算法。

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/a_star_path_planning.png" width="700px">
</div>

如何使用？如何您想在环境中增加障碍物，您可以去 ```simulator/simulator.py```:
```python
from entities.obstacle import SphericalObstacle, CubeObstacle

...

self.grid = grid_map()
self.obstacle_type = set()

# create spherical obstacle
num_of_spherical_obst = 2
center_list_so = [[200, 100, 30], [50, 10, 5]]
radius_list_so = [30, 10]
for i in range(num_of_spherical_obst):
    obst = SphericalObstacle(center_list_so[i], radius_list_so[i])
    obst.add_to_grid(self.grid)
    self.obstacle_type.add(obst.id)

# create cube obstacle
number_of_cube_obst = 3
center_list_co = [[50,50,1], [100,60,1],[160,96,1]]
length_list_co = [30, 10, 15]
width_list_co = [15, 15, 20]
height_list_co = [10, 20, 30]
for j in range(number_of_cube_obst):
    obst = CubeObstacle(center_list[j], length_list_co[j], width_list_co[j], height_list_co[j])
    obst.add_to_grid(self.grid)
    self.obstacle_type.add(obst.id)
```

在增加完障碍物之后，每一个无人机就可以调用路径规划算法去决定其最优路径 (在```entities/drone.py```中):
```python
from path_planning.astar import astar  # NOTE: REMEMBER TO IMPORT THE CORRESPONDING MODULE
from path_planning.path_following_3d import PathFollowing3D
from visualization.static_drawing import scatter_plot_with_obstacles

...

class Drone:
    ...

    path = astar.a_star_3d(self.start_coords, end_pos, self.simulator.grid)
    scatter_plot_with_obstacles(self.simulator, self.simulator.grid, [path])  # optional

    # the mobility model
    self.mobility_model = PathFollowing3D(self, path)

    ...
```
在执行完 ```scatter_plot_with_obstacles``` 函数之后，您将会看到障碍物以及对应的路径，如上图所示。  

## 能量模型
我们平台中目前所采用的无人机能量消耗模型基于Y. Zeng等人的文献 [8]。下图展示了不同飞行速度对应的功率消耗。因此飞行过程中的能量消耗就等于功率消耗乘以该速度下的飞行时间。  
<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/energy_model.png" width="400px">
</div>

## 移动控制
该平台还支持用户设计无人机集群网络的拓扑控制算法。当前版本实现了一种基于虚拟力的拓扑控制算法[9]，融合了区域中心点的吸引力和相邻无人机的排斥力。应用该算法，一个初始的、可能不连通的网络可以自组织成一个双连通网络。上图展示了移动控制后网络拓扑的变化。  
<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/virtual_force.png" width="800px">
</div>

如何使用？在```entities/drone.py```中，将```mobility_model```替换为```motion_controller```:  
```python
from topology.virtual_force.vf_motion_control import VfMotionController

class Drone:
  def __init__(self, env, node_id, coords, speed, inbox, simulator):
    ...
    # self.mobility_model = GaussMarkov3D(self)  REMEMBER TO COMMENT THIS SENTENCE OUT!
    self.motion_controller = VfMotionController(self)
    ...
```

## 可视化
该平台支持数据包传输过程的交互式可视化，以及展示无人机的飞行轨迹及网络拓扑结构。在这里，我要感谢@superboySB（戴子彭博士）为这个功能做出的贡献！  

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/visualization.gif" width="900px">
</div>

用户可以在```main.py``` 中启用该可视化功能：  
```python
import simpy
from utils import config
from simulator.simulator import Simulator
from visualization.visualizer import SimulationVisualizer

if __name__ == "__main__":
    # Simulation setup
    env = simpy.Environment()
    channel_states = {i: simpy.Resource(env, capacity=1) for i in range(config.NUMBER_OF_DRONES)}
    sim = Simulator(seed=2025, env=env, channel_states=channel_states, n_drones=config.NUMBER_OF_DRONES)
    
    # Add the visualizer to the simulator
    # Use 20000 microseconds (0.02s) as the visualization frame interval
    visualizer = SimulationVisualizer(sim, output_dir=".", vis_frame_interval=20000)
    visualizer.run_visualization()

    # Run simulation
    env.run(until=config.SIM_TIME)
    
    # Finalize visualization
    visualizer.finalize()
```

在这个项目的当前版本中，当用户运行```main.py```时，程序将显示无人机的初始位置分布图，然后关闭窗口，程序将继续运行。当仿真结束时，将显示无人机的飞行轨迹和无人机的最终位置，关闭这些窗口并等待一段时间，将显示交互窗口。  

## 表现评估
我们的 "UavNetSim-v1" 平台支持对多种指标的统计，如：  

- **Packet Delivery Ratio (PDR)**: PDR是所有目的地无人机成功接收到的数据包总数与所有源无人机产生的数据包总数的比值。值得注意的是，PDR的计算中排除了冗余数据包 (即重传的数据包)。PDR可以反映路由协议的可靠性。
- **Average End-to-End Delay (E2E Delay)**: 端到端延迟是数据包从源节点到达目的节点的平均时间延迟。通常，数据包传输中的延迟包括“排队延迟”、“接入延迟”、“传输延迟”、“传播延迟”和“处理延迟”。
- **Normalized Routing Load (NRL)**: NRL是所有无人机发送的所有路由控制数据包与目的无人机接收到的数据包数量的比值。
- **Average Throughput**: 在我们的平台中，吞吐量的计算是：每当目的地接收到一个数据包时，数据包的长度除以该数据包的端到端延迟（因为端到端延迟涉及该数据包的重传）。
- **Hop Count**: 跳数是数据包传输过程中所经过的中间节点的数量。

## 设计你自己的协议
我们的仿真平台可以根据您的研究需求进行扩展，包括设计您自己的无人机移动模型（在```mobility```文件夹中），mac协议（在```mac```文件夹中），路由协议（在```routing```文件夹中），等等。我们以路由协议为例，介绍用户如何设计自己的算法。  

* 在 ```routing```文件夹下创建一个新的package
* 路由协议的主程序必须包括```def next_hop_selection(self, packet)``` 和 ```def packet_reception(self, packet, src_drone_id)```两个函数
* 在确认路由逻辑正确后，您可以在```drone.py```中导入您自己的路由模块：
 ```python
   from routing.dsdv.dsdv import Dsdv  # import your module
   ...
   class Drone:
     def __init__(self, env, node_id, coords, speed, inbox, simulator):
       ...
       self.routing_protocol = Dsdv(self.simulator, self)  # install
       ...
   ```

## 参考文献
[1] C. Perkins and P. Bhagwat, "[Highly dynamic destination-sequenced distance-vector routing (DSDV) for mobile computers](https://dl.acm.org/doi/abs/10.1145/190809.190336)," in *ACM SIGCOMM Computer Communication Review*, vol. 24, no. 4, pp. 234-244, 1994.  
[2] R. Poor, "Gradient routing in ad hoc networks", 2000, [www.media.mit.edu/pia/Research/ESP/texts/poorieeepaper.pdf](www.media.mit.edu/pia/Research/ESP/texts/poorieeepaper.pdf)  
[3] J. Boyan and M. Littman, "[Packet routing in dynamically changing networks: A reinforcement learning approach](https://proceedings.neurips.cc/paper/1993/hash/4ea06fbc83cdd0a06020c35d50e1e89a-Abstract.html)" in *Advances in Neural Information Processing Systems*, vol. 6, 1993.  
[4] W. S. Jung, J. Yim and Y. B. Ko, "[QGeo: Q-learning-based geographic ad hoc routing protocol for unmanned robotic networks](https://ieeexplore.ieee.org/abstract/document/7829268/)," in *IEEE Communications Letters*, vol. 21, no. 10, pp. 2258-2261, 2017.  
[5] M. Gharib, F. Afghah and E. Bentley, "[Opar: Optimized predictive and adaptive routing for cooperative uav networks](https://ieeexplore.ieee.org/abstract/document/9484489)," in *IEEE INFOCOM 2021-IEEE Conference on Computer Communications Workshops (INFOCOM WKSHPS)*, pp. 1-6, 2021.  
[6] A. Colvin, "[CSMA with collision avoidance](cn.overleaf.com/project/678e52bd44cc7c6c70e39d90)," *Computer Communications*, vol. 6, no. 5, pp. 227-235, 1983.  
[7] N. Abramson, "[The ALOHA system: Another alternative for computer communications](n.overleaf.com/project/678e52bd44cc7c6c70e39d90)," in *Proceedings of the November 17-19, 1970, Fall Joint Computer Conference*, pp. 281-285, 1970.  
[8] Y. Zeng, J. Xu and R. Zhang, "[Energy minimization for wireless communication with rotary-wing UAV](https://ieeexplore.ieee.org/document/8663615)," in *IEEE transactions on wireless communications*, vol. 18, no. 4, pp. 2329-2345, 2019.  
[9] H. Liu, X. Chu, Y. -W. Leung and R. Du, "[Simple movement control algorithm for bi-connectivity in robotic sensor networks](https://ieeexplore.ieee.org/document/5555924)," in *IEEE Journal on Selected Areas in Communications*, vol. 28, no. 7, pp. 994-1005, 2010.  

## 贡献
欢迎大家对该平台提交新的功能！

## 如何引用该工作
如何您觉得该项目对您的科研带来了帮助，欢迎引用我们的论文：
```
@inproceedings{zhou2025uavnetsim,
    title={UavNetSim-v1: A Python-based Simulation Platform for UAV Communication Networks},
    author={Zhou, Zihao and Dai, Zipeng and Huang, Linyi and Yang, Cui and Xiang, Youjun and Tang, Jie and Wong, Kai-kit},
    booktitle={14-th IEEE/CIC International Conference on Communications in China},
    address = {Shanghai, China},
    month = {August},
    year = {2025}
}
```
或 
```
@article{zhou2025uavnetsim,
  title={UavNetSim-v1: A Python-based Simulation Platform for UAV Communication Networks},
  author={Zhou, Zihao and Dai, Zipeng and Huang, Linyi and Yang, Cui and Xiang, Youjun and Tang, Jie and Wong, Kai-kit},
  journal={arXiv preprint arXiv:2507.09852},
  year={2025}
}
```

## 支持与鼓励
如果您觉得该项目有帮助，欢迎给一个star！

## License
This project is MIT-licensed.

