# Place this in app/src/main/python/navigation_logic.py
import numpy as np
import cv2
import math

# Import your other modules
from qr_detection import QRDetectionModule
from qr_decoder import QRDecoder
from route_guidance import RouteGuidance

class NavigationProcessor:
    """
    Main class to process navigation logic.
    An instance of this will be created in Java.
    """
    def __init__(self):
        self.detector = QRDetectionModule()
        self.decoder = QRDecoder()
        self.route_guidance = RouteGuidance()
        self.current_location = None
        self.destination_id = None
        self.current_path = []
        print("Python NavigationProcessor Initialized")

    def set_destination(self, destination_id: str):
        """Sets the user's destination. Called from Java."""
        if destination_id in self.decoder.location_database:
            self.destination_id = destination_id
            print(f"Destination set to: {self.destination_id}")
            self.current_path = [] # Clear old path
            return True
        print(f"Error: Destination '{destination_id}' not found.")
        return False

    def process_frame(self, image_bytes: bytes, width: int, height: int):
        """The main method called from Java for every camera frame."""
        try:
            # 1. Convert camera frame from Java (YUV_420_888/NV21) to OpenCV format
            yuv = np.frombuffer(image_bytes, dtype=np.uint8).reshape(height + height // 2, width)
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_NV21)

            # 2. Detect the nearest QR code
            nearest_qr = self.detector.get_nearest_qr(self.detector.detect_qr_codes(frame))
            if not nearest_qr:
                return None

            # 3. Read QR and update location
            location_info = self.decoder.read_qr_code(nearest_qr, frame)
            if location_info and (not self.current_location or self.current_location.location_id != location_info.location_id):
                self.current_location = location_info
                print(f"Location updated: {self.current_location.location_name}")
                if self.destination_id:
                    nav_data = self.route_guidance.prepare_navigation_data(self.current_location.location_id, self.destination_id)
                    if nav_data and nav_data.get("path"):
                        self.current_path = nav_data["path"]
                        print(f"New path: {' -> '.join(self.current_path)}")

            # 4. Check conditions for navigation
            if not self.current_location or not self.current_path:
                return None

            if self.current_location.location_id == self.destination_id:
                return {"target_azimuth": -1.0, "target_distance": -1.0} # "Destination Reached" code

            # 5. Get next waypoint and calculate guidance
            current_index = self.current_path.index(self.current_location.location_id)
            next_waypoint_id = self.current_path[current_index + 1] if current_index + 1 < len(self.current_path) else self.destination_id
            next_waypoint_info = self.decoder.location_database.get(next_waypoint_id)
            if not next_waypoint_info: return None

            current_coords = self.current_location.coordinates
            next_coords = next_waypoint_info.coordinates

            # Bearing needs (lat, lon) which corresponds to (y, x)
            target_azimuth = math.degrees(math.atan2(next_coords[0] - current_coords[0], next_coords[1] - current_coords[1]))
            target_azimuth = (target_azimuth + 360) % 360

            distance_meters = math.sqrt((next_coords[0] - current_coords[0])**2 + (next_coords[1] - current_coords[1])**2)

            # 6. Return data as a Python dictionary
            return {"target_azimuth": target_azimuth, "target_distance": distance_meters}

        except Exception as e:
            print(f"Python Error: {e}") # This will show up in Android's logcat
            return None