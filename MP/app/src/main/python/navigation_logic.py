# In app/src/main/python/navigation_logic.py

import numpy as np
import cv2
import math

# Import all your team's existing modules
from qr_detection import QRDetectionModule
from qr_decoder import QRDecoder
from route_guidance import RouteGuidance

class NavigationProcessor:
    """
    Main class to process navigation logic.
    An instance of this will be created and used by the Java code.
    """
    def __init__(self):
        """Initializes all Python modules."""
        self.detector = QRDetectionModule()
        self.decoder = QRDecoder()
        self.route_guidance = RouteGuidance()
        self.current_location = None
        self.destination_id = None
        self.current_path = []
        print("Python: NavigationProcessor Initialized Successfully")

    def set_destination(self, destination_id: str):
        """
        Sets the user's desired destination. This will be called from Java.
        """
        if destination_id in self.decoder.location_database:
            self.destination_id = destination_id
            print(f"Python: Destination set to '{self.destination_id}'")
            self.current_path = [] # Clear old path
            return True
        else:
            print(f"Python: Error - Destination '{destination_id}' not found.")
            return False

    def _calculate_bearing(self, coords1, coords2):
        """Calculates the compass bearing from point 1 to point 2."""
        # Standard bearing calculation: atan2(dx, dy)
        lat1, lon1 = coords1[1], coords1[0]
        lat2, lon2 = coords2[1], coords2[0]
        angle = math.degrees(math.atan2(lon2 - lon1, lat2 - lat1))
        return (angle + 360) % 360 # Normalize to 0-360 degrees

    def process_frame(self, image_bytes: bytes, width: int, height: int):
        """
        The main method called from Java for every camera frame.
        """
        try:
            # 1. Convert camera frame from Java (YUV_420_888/NV21) to OpenCV's BGR format
            yuv = np.frombuffer(image_bytes, dtype=np.uint8).reshape(height + height // 2, width)
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_NV21)

            # 2. Detect the nearest QR code
            nearest_qr = self.detector.get_nearest_qr(self.detector.detect_qr_codes(frame))
            if not nearest_qr:
                return None # No QR code in sight

            # 3. Read the QR code to update our current location
            location_info = self.decoder.read_qr_code(nearest_qr, frame)
            
            if location_info and (not self.current_location or self.current_location.location_id != location_info.location_id):
                self.current_location = location_info
                print(f"Python: Location updated to {self.current_location.location_name}")
                
                if self.destination_id:
                    nav_data = self.route_guidance.prepare_navigation_data(
                        self.current_location.location_id, self.destination_id
                    )
                    if nav_data and nav_data.get("path"):
                        self.current_path = nav_data["path"]
                        print(f"Python: New path planned: {' -> '.join(self.current_path)}")

            # 4. If we don't have a path or a current location, we can't navigate.
            if not self.current_location or not self.current_path:
                return None

            # 5. Check if we have arrived at the final destination
            if self.current_location.location_id == self.destination_id:
                print("Python: Destination reached!")
                return {"target_azimuth": -1.0, "target_distance": -1.0} # Special code for "done"

            # 6. Find the next waypoint in our path
            try:
                current_index = self.current_path.index(self.current_location.location_id)
                next_waypoint_id = self.current_path[current_index + 1] if current_index + 1 < len(self.current_path) else self.destination_id
            except ValueError:
                print("Python: Off track! Current location not in path.")
                return None

            next_waypoint_info = self.decoder.location_database.get(next_waypoint_id)
            if not next_waypoint_info: return None
            
            # 7. Calculate Azimuth and Distance to the next waypoint
            current_coords = self.current_location.coordinates
            next_coords = next_waypoint_info.coordinates
            
            target_azimuth = self._calculate_bearing(current_coords, next_coords)
            distance_meters = math.sqrt((next_coords[0] - current_coords[0])**2 + (next_coords[1] - current_coords[1])**2)
            
            # 8. Return the data to Java as a dictionary
            return {"target_azimuth": target_azimuth, "target_distance": distance_meters}

        except Exception as e:
            print(f"Python Error in process_frame: {e}") # This will show in Android's Logcat
            return None

    # In app/src/main/python/navigation_logic.py
    # Add this method inside the NavigationProcessor class

    def get_all_locations(self):
        """
        Returns a dictionary of all available locations for the destination list.
        Key: location_id, Value: location_name.
        This will be called from Java to populate the selection screen.
        """
        if not self.decoder.location_database:
            return {}

        # Create a dictionary of { "N_G_LAB_101": "Computer Lab 101", ... }
        locations = {
            loc_id: loc.location_name
            for loc_id, loc in self.decoder.location_database.items()
        }
        return locations