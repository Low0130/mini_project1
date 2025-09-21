import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import List, Optional

class BuildingMap:
    def __init__(self):
        self.bottom_rooms = [
            {'name': 'N101', 'location_id': 'N_G_LAB_101', 'x': 0, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Wheelchair accessible'},
            {'name': 'N102', 'location_id': 'N_G_LAB_102', 'x': 3, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Wheelchair accessible'},
            {'name': 'N103', 'location_id': 'N_G_OFFICE_103', 'x': 6, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Accessible'},
            {'name': 'N104', 'location_id': 'N_G_OFFICE_104', 'x': 12, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Accessible'},
            {'name': 'N105', 'location_id': 'N_G_OFFICE_105', 'x': 15, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Accessible'},
            {'name': 'N106', 'location_id': 'N_G_OFFICE_106', 'x': 18, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Accessible'},
            {'name': 'N107', 'location_id': 'N_G_OFFICE_107', 'x': 21, 'y': 0, 'width': 3, 'height': 2, 'qr_orientation': 0.0, 'accessibility_info': 'Accessible'},
        ]
        self.top_rooms = [
            {'name': 'NFT1', 'location_id': 'N_G_RESTROOM_F', 'x': 1.5, 'y': 6, 'width': 0.75, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible restroom'},
            {'name': 'NFT2', 'location_id': 'N_G_RESTROOM_M', 'x': 2.25, 'y': 7, 'width': 1.5, 'height': 1, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible restroom'},
            {'name': 'N112B', 'location_id': 'N_G_OFFICE_112B', 'x': 3.75, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N112A', 'location_id': 'N_G_OFFICE_112A', 'x': 5.25, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N111', 'location_id': 'N_G_OFFICE_111', 'x': 6.75, 'y': 6, 'width': 2.25, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N110B', 'location_id': 'N_G_OFFICE_110B', 'x': 12, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N110A', 'location_id': 'N_G_OFFICE_110A', 'x': 13.5, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N109A', 'location_id': 'N_G_OFFICE_109A', 'x': 15, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'N109B', 'location_id': 'N_G_OFFICE_109B', 'x': 16.5, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'NFT4', 'location_id': 'N_G_RESTROOM_F2', 'x': 18, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible restroom'},
            {'name': 'NFT5', 'location_id': 'N_G_RESTROOM_M2', 'x': 19.5, 'y': 6, 'width': 1.5, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible restroom'},
            {'name': 'N108', 'location_id': 'N_G_OFFICE_108', 'x': 21, 'y': 6, 'width': 3, 'height': 2, 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
        ]
        self.special_areas = [
            {'name': 'Stair 1', 'location_id': 'N_G_STAIR_1', 'x': 9, 'y': 0, 'width': 3, 'height': 2, 'color': '#9999FF', 'qr_orientation': 0.0, 'accessibility_info': 'Not accessible'},
            {'name': 'Sitting area 2', 'location_id': 'N_G_SITTING_2', 'x': 7, 'y': 3, 'width': 3, 'height': 2, 'color': '#FFFF99', 'qr_orientation': 90.0, 'accessibility_info': 'Accessible'},
            {'name': 'Stair 2', 'location_id': 'N_G_STAIR_2', 'x': 12, 'y': 3, 'width': 6, 'height': 2, 'color': '#9999FF', 'qr_orientation': 90.0, 'accessibility_info': 'Not accessible'},
            {'name': 'Stair 3', 'location_id': 'N_G_STAIR_3', 'x': 0, 'y': 6, 'width': 1.5, 'height': 2, 'color': '#9999FF', 'qr_orientation': 180.0, 'accessibility_info': 'Not accessible'},
            {'name': 'Sitting area 1', 'location_id': 'N_G_SITTING_1', 'x': 9, 'y': 6, 'width': 3, 'height': 2, 'color': '#FFFF99', 'qr_orientation': 180.0, 'accessibility_info': 'Accessible'},
            {'name': 'Other area', 'location_id': 'N_G_OTHER', 'x': 24, 'y': 3, 'width': 1.5, 'height': 2, 'color': '#CCCCCC', 'qr_orientation': 90.0, 'accessibility_info': 'Accessible'},
        ]
        self.nodes = {
            'N_G_LAB_101': (1.5, 2.2),
            'N_G_LAB_102': (4.5, 2.2),
            'N_G_OFFICE_103': (7.5, 2.2),
            'N_G_OFFICE_104': (13.5, 2.2),
            'N_G_OFFICE_105': (16.5, 2.2),
            'N_G_OFFICE_106': (19.5, 2.2),
            'N_G_OFFICE_107': (22.5, 2.2),
            'N_G_RESTROOM_F': (1.875, 5.8),
            'N_G_RESTROOM_M': (3.0, 5.8),
            'N_G_OFFICE_112B': (4.5, 5.8),
            'N_G_OFFICE_112A': (6.0, 5.8),
            'N_G_OFFICE_111': (7.875, 5.8),
            'N_G_OFFICE_110B': (12.75, 5.8),
            'N_G_OFFICE_110A': (14.25, 5.8),
            'N_G_OFFICE_109A': (15.75, 5.8),
            'N_G_OFFICE_109B': (17.25, 5.8),
            'N_G_RESTROOM_F2': (18.75, 5.8),
            'N_G_RESTROOM_M2': (20.25, 5.8),
            'N_G_OFFICE_108': (22.5, 5.8),
            'N_G_STAIR_1': (10.5, 2.2),
            'N_G_SITTING_2': (10.5, 4),
            'N_G_STAIR_2': (10.5, 4),
            'N_G_STAIR_3': (0.75, 5.8),
            'N_G_SITTING_1': (10.5, 5.8),
            'N_G_OTHER': (24.75, 4),
        }

    def plot_map(self, path: Optional[List[str]] = None, filename: str = "map.png"):
        fig, ax = plt.subplots(1, 1, figsize=(18, 10))
        room_color = '#90EE90'
        toilet_color = '#FFB6C1'
        special_color = '#FFFF99'
        stair_color = '#9999FF'
        node_color = '#87CEEB'
        path_color = '#0000FF'
        route_color = '#FF0000'

        # Draw rooms
        all_rooms = self.bottom_rooms + self.top_rooms
        for room in all_rooms:
            color = toilet_color if "NFT" in room['name'] else room_color
            rect = mpatches.Rectangle((room['x'], room['y']), room['width'], room['height'],
                                     linewidth=2, edgecolor='black', facecolor=color)
            ax.add_patch(rect)
            ax.text(room['x'] + room['width']/2, room['y'] + room['height']/2,
                    room['name'], ha='center', va='center', fontsize=9, weight='bold')

        # Draw special areas
        for area in self.special_areas:
            rect = mpatches.Rectangle((area['x'], area['y']), area['width'], area['height'],
                                     linewidth=2, edgecolor='black', facecolor=area['color'])
            ax.add_patch(rect)
            ax.text(area['x'] + area['width']/2, area['y'] + area['height']/2,
                    area['name'], ha='center', va='center', fontsize=8, weight='bold')

        # Draw nodes
        for x, y in self.nodes.values():
            circle = mpatches.Circle((x, y), 0.12, color=node_color, ec='black', linewidth=1.5)
            ax.add_patch(circle)

        # Draw paths
        ax.plot([0.75, 22.5], [2.2, 2.2], color=path_color, linewidth=3, label='Corridor')
        ax.plot([0.75, 22.5], [5.8, 5.8], color=path_color, linewidth=3)
        ax.plot([0.75, 0.75], [2.2, 5.8], color=path_color, linewidth=3)
        ax.plot([22.5, 22.5], [2.2, 5.8], color=path_color, linewidth=3)
        ax.plot([10.5, 10.5], [2.2, 5.8], color=path_color, linewidth=3)

        # Highlight route if provided
        if path:
            for i in range(len(path) - 1):
                loc1, loc2 = path[i], path[i + 1]
                x1, y1 = self.nodes[loc1]
                x2, y2 = self.nodes[loc2]
                ax.plot([x1, x2], [y1, y2], color=route_color, linewidth=4, zorder=10, label='Route' if i == 0 else '')

        # Add legend
        ax.legend(loc='upper right', fontsize=10)
        ax.set_xlim(-1, 26)
        ax.set_ylim(-1, 9)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title('Ground Floor Layout - Block N', fontsize=14, weight='bold')
        plt.tight_layout()
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

if __name__ == "__main__":
    building_map = BuildingMap()
    building_map.plot_map()