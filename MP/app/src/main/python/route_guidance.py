import math
import heapq
import logging
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from map_building import BuildingMap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NavigationInstruction:
    action: str
    angle: float
    distance: float
    direction_name: str
    description: str
    confidence: float
    next_landmark: str
    
    def get_voice_instruction(self) -> str:
        if self.action == "turn_left":
            return f"Turn left {self.angle:.0f} degrees to face {self.direction_name}"
        elif self.action == "turn_right":
            return f"Turn right {self.angle:.0f} degrees to face {self.direction_name}"
        elif self.action == "go_straight":
            return f"Go straight ahead toward {self.direction_name} for {self.distance:.1f} meters"
        elif self.action == "face_direction":
            return f"Face {self.direction_name}"
        else:
            return self.description

class RouteGuidance:
    def __init__(self, output_dir: str = "."):
        self.building_map = BuildingMap()
        self.nodes = self.building_map.nodes
        self.graph = self._build_graph()
        self.location_database = self._build_location_database()
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

    def _build_graph(self) -> Dict[str, List[Tuple[str, float]]]:
        """构建图结构，修正了连接逻辑"""
        graph = {loc_id: [] for loc_id in self.nodes}
        
        # 定义走廊路径 - 修正顺序和连接
        horizontal_bottom = [
            'N_G_LAB_101', 'N_G_LAB_102', 'N_G_OFFICE_103', 'N_G_STAIR_1',
            'N_G_OFFICE_104', 'N_G_OFFICE_105', 'N_G_OFFICE_106', 'N_G_OFFICE_107'
        ]
        horizontal_top = [
            'N_G_STAIR_3', 'N_G_RESTROOM_F', 'N_G_RESTROOM_M', 'N_G_OFFICE_112B',
            'N_G_OFFICE_112A', 'N_G_OFFICE_111', 'N_G_SITTING_1', 'N_G_OFFICE_110B',
            'N_G_OFFICE_110A', 'N_G_OFFICE_109A', 'N_G_OFFICE_109B', 'N_G_RESTROOM_F2',
            'N_G_RESTROOM_M2', 'N_G_OFFICE_108'
        ]
        
        # 垂直连接 - 修正连接点
        vertical_connections = [
            ('N_G_LAB_101', 'N_G_STAIR_3'),  # 左侧垂直连接
            ('N_G_STAIR_1', 'N_G_SITTING_2'),  # 中间垂直连接1
            ('N_G_SITTING_2', 'N_G_STAIR_2'),  # 中间垂直连接2 
            ('N_G_STAIR_2', 'N_G_SITTING_1'),  # 中间垂直连接3
            ('N_G_OFFICE_107', 'N_G_OFFICE_108'),  # 右侧垂直连接
            ('N_G_OFFICE_108', 'N_G_OTHER')  # 连接到其他区域
        ]

        def add_connection(loc1: str, loc2: str):
            """添加双向连接"""
            if loc1 not in self.nodes or loc2 not in self.nodes:
                logger.warning(f"Node {loc1} or {loc2} not found in nodes")
                return
            
            # 计算欧几里得距离
            x1, y1 = self.nodes[loc1]
            x2, y2 = self.nodes[loc2]
            dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            graph[loc1].append((loc2, dist))
            graph[loc2].append((loc1, dist))

        # 添加水平连接
        for path in [horizontal_bottom, horizontal_top]:
            for i in range(len(path) - 1):
                add_connection(path[i], path[i + 1])

        # 添加垂直连接
        for loc1, loc2 in vertical_connections:
            add_connection(loc1, loc2)

        # 添加特殊连接 - 修正SITTING_2和STAIR_2的重复坐标问题
        # SITTING_2和STAIR_2在map_building.py中有相同坐标，需要特殊处理
        special_connections = [
            ('N_G_SITTING_2', 'N_G_OFFICE_104'),  # 连接到附近的办公室
            ('N_G_SITTING_2', 'N_G_OFFICE_105'),
            ('N_G_STAIR_2', 'N_G_OFFICE_110B'),   # 连接到上层附近的办公室
            ('N_G_STAIR_2', 'N_G_OFFICE_110A')
        ]
        
        for loc1, loc2 in special_connections:
            add_connection(loc1, loc2)

        return graph

    def _build_location_database(self) -> Dict[str, Dict[str, Any]]:
        """构建位置数据库，修正了方向计算"""
        location_database = {}
        all_locations = self.building_map.bottom_rooms + self.building_map.top_rooms + self.building_map.special_areas
        
        for loc in all_locations:
            loc_id = loc['location_id']
            if loc_id not in self.nodes:
                logger.warning(f"Location {loc_id} not found in nodes")
                continue
            
            # 获取连接的节点
            connections = [n for n, _ in self.graph.get(loc_id, [])]
            
            # 计算到每个相邻节点的方向角度
            directions = {}
            x, y = self.nodes[loc_id]
            
            for neighbor_id in connections:
                if neighbor_id not in self.nodes:
                    continue
                    
                nx, ny = self.nodes[neighbor_id]
                # 计算方向角度 (以东为0度，逆时针为正)
                angle = math.degrees(math.atan2(ny - y, nx - x))
                # 转换为0-360度范围
                if angle < 0:
                    angle += 360
                directions[neighbor_id] = angle
            
            location_database[loc_id] = {
                'location_id': loc_id,
                'location_name': loc['name'],
                'coordinates': self.nodes[loc_id],
                'available_directions': directions,
                'connections': connections,
                'qr_orientation': loc.get('qr_orientation', 0.0)
            }
        
        return location_database

    def find_shortest_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """使用Dijkstra算法找最短路径"""
        if start_id not in self.graph or end_id not in self.graph:
            logger.error(f"Invalid start or end node: {start_id}, {end_id}")
            return None
        
        if start_id == end_id:
            return [start_id]
        
        # 初始化距离和前驱节点
        distances = {node: float('inf') for node in self.graph}
        distances[start_id] = 0
        predecessors = {node: None for node in self.graph}
        
        # 优先队列
        pq = [(0, start_id)]
        visited = set()
        
        while pq:
            current_distance, current_node = heapq.heappop(pq)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            
            # 到达目标
            if current_node == end_id:
                break
            
            # 检查所有邻居
            for neighbor, weight in self.graph.get(current_node, []):
                if neighbor in visited:
                    continue
                    
                distance = current_distance + weight
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(pq, (distance, neighbor))
        
        # 检查是否找到路径
        if distances[end_id] == float('inf'):
            logger.error(f"No path found from {start_id} to {end_id}")
            return None
        
        # 重建路径
        path = []
        current_node = end_id
        while current_node is not None:
            path.append(current_node)
            current_node = predecessors[current_node]
        
        return path[::-1]  # 反转以获得从起点到终点的路径

    def calculate_alignment_instruction(self, current_location_id: str, current_facing: float, 
                                      target_direction: str) -> Optional[NavigationInstruction]:
        """计算对齐指令 - 修正了角度计算"""
        if current_location_id not in self.location_database:
            logger.error(f"Current location {current_location_id} not in database")
            return None
        
        current_location = self.location_database[current_location_id]
        
        if target_direction not in current_location['available_directions']:
            logger.error(f"Target direction {target_direction} not available from {current_location_id}")
            return None
        
        # 获取目标方向的角度
        target_angle = current_location['available_directions'][target_direction]
        
        # 计算需要转向的角度差
        angle_diff = target_angle - current_facing
        
        # 标准化角度到[-180, 180]范围
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        
        # 计算到目标的距离
        distance = 0
        if current_location_id != target_direction and target_direction in self.nodes:
            loc1 = current_location['coordinates']
            loc2 = self.nodes[target_direction]
            distance = math.sqrt((loc2[0] - loc1[0])**2 + (loc2[1] - loc1[1])**2)
        
        # 生成导航指令
        if abs(angle_diff) < 10:  # 允许10度误差
            return NavigationInstruction(
                action="go_straight",
                angle=0,
                distance=distance,
                direction_name=target_direction,
                description=f"Proceed straight toward {target_direction}",
                confidence=0.95,
                next_landmark=self.location_database.get(target_direction, {}).get('location_name', target_direction)
            )
        elif angle_diff > 0:
            return NavigationInstruction(
                action="turn_right",
                angle=abs(angle_diff),
                distance=0,
                direction_name=target_direction,
                description=f"Turn right {abs(angle_diff):.0f} degrees toward {target_direction}",
                confidence=0.9,
                next_landmark=self.location_database.get(target_direction, {}).get('location_name', target_direction)
            )
        else:
            return NavigationInstruction(
                action="turn_left",
                angle=abs(angle_diff),
                distance=0,
                direction_name=target_direction,
                description=f"Turn left {abs(angle_diff):.0f} degrees toward {target_direction}",
                confidence=0.9,
                next_landmark=self.location_database.get(target_direction, {}).get('location_name', target_direction)
            )

    def prepare_navigation_data(self, current_location_id: str, destination_id: str) -> Optional[Dict[str, Any]]:
        """准备导航数据 - 修正了错误处理"""
        if not current_location_id or not destination_id:
            logger.error("Invalid current_location_id or destination_id")
            return None
        
        if current_location_id not in self.location_database:
            logger.error(f"Current location {current_location_id} not in database")
            return None
            
        if destination_id not in self.location_database:
            logger.error(f"Destination {destination_id} not in database")
            return None
        
        # 查找路径
        path = self.find_shortest_path(current_location_id, destination_id)
        if not path:
            logger.error(f"No valid path from {current_location_id} to {destination_id}")
            return None
        
        # 生成地图
        try:
            map_path = os.path.join(self.output_dir, "map.png")
            self.building_map.plot_map(path, map_path)
            logger.info(f"Map with route saved to {map_path}")
        except Exception as e:
            logger.error(f"Failed to save map: {e}")
            # 不要因为地图保存失败而返回None，导航数据仍然有效
        
        # 计算路径总距离
        total_distance = 0
        for i in range(len(path) - 1):
            loc1 = self.nodes[path[i]]
            loc2 = self.nodes[path[i + 1]]
            total_distance += math.sqrt((loc2[0] - loc1[0])**2 + (loc2[1] - loc1[1])**2)
        
        return {
            "current_location_id": current_location_id,
            "destination_id": destination_id,
            "path": path,
            "total_distance": total_distance,
            "location_database": self.location_database,
            "instructions": self._generate_step_by_step_instructions(path)
        }
    
    def _generate_step_by_step_instructions(self, path: List[str]) -> List[str]:
        """生成逐步导航指令"""
        instructions = []
        
        for i in range(len(path) - 1):
            current = path[i]
            next_location = path[i + 1]
            
            current_info = self.location_database.get(current, {})
            next_info = self.location_database.get(next_location, {})
            
            current_name = current_info.get('location_name', current)
            next_name = next_info.get('location_name', next_location)
            
            if i == 0:
                instructions.append(f"Starting from {current_name}")
            
            instructions.append(f"Proceed to {next_name}")
        
        if path:
            final_name = self.location_database.get(path[-1], {}).get('location_name', path[-1])
            instructions.append(f"Arrive at destination: {final_name}")
        
        return instructions

    def get_next_instruction(self, current_location_id: str, path: List[str]) -> Optional[str]:
        """获取下一步指令"""
        try:
            current_index = path.index(current_location_id)
            if current_index < len(path) - 1:
                next_location = path[current_index + 1]
                next_name = self.location_database.get(next_location, {}).get('location_name', next_location)
                return f"Next: Head to {next_name} ({next_location})"
            else:
                return "You have reached your destination!"
        except ValueError:
            return "Current location not found in path"
        
    def _calculate_bearing(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """
        Helper to calculate the bearing (azimuth) from pos1 to pos2.
        Azimuth is degrees from North (Y-axis), clockwise.
        """
        x1, y1 = pos1
        x2, y2 = pos2
        # atan2 takes (y, x), so we use (x2 - x1, y2 - y1) to get angle from the Y-axis (North)
        angle = math.degrees(math.atan2(x2 - x1, y2 - y1))
        # Normalize to 0-360 degrees
        if angle < 0:
            angle += 360
        return angle

if __name__ == "__main__":
    guidance = RouteGuidance()
    
    # 测试路径查找
    print("Testing route guidance...")
    path = guidance.find_shortest_path('N_G_LAB_101', 'N_G_OFFICE_108')
    print(f"Path from N_G_LAB_101 to N_G_OFFICE_108: {path}")
    
    # 测试导航数据准备
    nav_data = guidance.prepare_navigation_data('N_G_LAB_101', 'N_G_OFFICE_108')
    if nav_data:
        print(f"Navigation prepared successfully")
        print(f"Total distance: {nav_data['total_distance']:.2f} units")
        print("Step-by-step instructions:")
        for instruction in nav_data['instructions']:
            print(f"  - {instruction}")
    else:
        print("Failed to prepare navigation data")