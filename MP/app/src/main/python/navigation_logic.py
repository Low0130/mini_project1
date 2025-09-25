# navigation_logic.py

import cv2
import numpy as np
import traceback
import math
from typing import Dict, Any, Optional, List

# Assuming these modules are in the same directory within the Android project
from map_building import BuildingMap
from qr_detection import QRDetectionModule
from qr_decoder import QRDecoder, LocationInfo
from route_guidance import RouteGuidance

class NavigationProcessor:
    """
    Manages the entire navigation lifecycle for an Android application.
    """
    def __init__(self):
        print("Python: Initializing NavigationProcessor...")
        try:
            self.detector = QRDetectionModule()
            self.decoder = QRDecoder()
            self.guidance = RouteGuidance()
            self.current_location: Optional[LocationInfo] = None
            self.destination_id: Optional[str] = None
            self.current_path: Optional[List[str]] = None
            print("Python: NavigationProcessor initialized successfully.")
        except Exception as e:
            print(f"PYTHON CRITICAL: Failed to initialize NavigationProcessor: {e}")
            traceback.print_exc()

    def get_all_locations(self) -> Dict[str, Any]:
        print("Python: get_all_locations called.")
        locations = []
        for loc_id, loc_data in self.guidance.location_database.items():
            locations.append({
                "location_id": loc_id,
                "location_name": loc_data.get('location_name', 'Unknown')
            })
        print(f"Python: Found {len(locations)} locations to send to Java.")
        return {"locations": locations}

    def set_destination(self, destination_id: str) -> Dict[str, Any]:
        print(f"Python: set_destination called with ID: {destination_id}")
        if not self.current_location:
            return {"status": "ERROR", "message": "Current location is unknown. Scan a QR code first."}

        self.destination_id = destination_id
        nav_data = self.guidance.prepare_navigation_data(
            self.current_location.location_id,
            self.destination_id
        )
        if nav_data and nav_data.get("path"):
            self.current_path = nav_data["path"]
            print(f"Python: Path planned successfully: {' -> '.join(self.current_path)}")
            return {"status": "PATH_READY", "message": "Path calculated successfully.", "path": self.current_path}
        else:
            print("Python Error: Failed to find a path.")
            self.current_path = None
            return {"status": "ERROR", "message": f"Could not find a path to {destination_id}."}

    def process_camera_frame(self, image_bytes: bytes, width: int, height: int) -> Dict[str, Any]:
        try:
            expected_size = int(width * height * 1.5)
            if len(image_bytes) != expected_size:
                return {"status": "ERROR", "message": f"Incorrect buffer size. Expected {expected_size}, got {len(image_bytes)}."}
            yuv_image = np.frombuffer(image_bytes, dtype=np.uint8).reshape(height + height // 2, width)
            bgr_frame = cv2.cvtColor(yuv_image, cv2.COLOR_YUV2BGR_NV21)
            resized_frame = cv2.resize(bgr_frame, (self.detector.frame_width, self.detector.frame_height))

            targets = self.detector.detect_qr_codes(resized_frame)
            nearest_qr = self.detector.get_nearest_qr(targets)
            if not nearest_qr:
                return {"status": "SCANNING"}

            qr_corners = nearest_qr.corners
            location_info = self.decoder.read_qr_code(nearest_qr, resized_frame)
            if not location_info:
                return {"status": "DETECTED", "corners": qr_corners}

            # --- This is the core state update ---
            is_new_location = self.current_location is None or self.current_location.location_id != location_info.location_id
            if is_new_location:
                print(f"Python: Location updated to {location_info.location_name} ({location_info.location_id})")
                self.current_location = location_info

            # Always call the state machine to get the correct status to return
            return self._update_navigation_status(qr_corners)

        except Exception as e:
            print(f"PYTHON CRASH: An error occurred in process_camera_frame: {e}")
            traceback.print_exc()
            return {"status": "ERROR", "message": f"An internal Python error occurred: {e}"}

    def _update_navigation_status(self, corners: List) -> Dict[str, Any]:
        """
        Private helper to determine the navigation state after a location has been confirmed.
        This is the final, robust state machine.
        """
        if not self.current_location:
            return {"status": "ERROR", "message": "Critical: current_location is None."}

        # Default result is to confirm the user's location.
        # This is the state when the path hasn't been planned yet.
        result = {
            "status": "LOCATION_CONFIRMED",
            "location_name": self.current_location.location_name,
            "location_id": self.current_location.location_id,
            "corners": corners
        }

        # Now, check if we are in an active navigation session (a path exists).
        if self.current_path:
            # State 1: Check for arrival at the final destination.
            if self.current_location.location_id == self.destination_id:
                result = {"status": "ARRIVED", "location_name": self.current_location.location_name, "corners": corners}

            # State 2: Check if the current location is on the planned path.
            elif self.current_location.location_id not in self.current_path:
                print("Python: User is off track.")
                replan_result = self.set_destination(self.destination_id) # Attempt to replan
                if replan_result.get("status") == "PATH_READY":
                    result = {"status": "OFF_TRACK_RECALCULATED", "new_path": replan_result.get("path"), "corners": corners}
                else:
                    result = {"status": "OFF_TRACK_ERROR", "message": "Off track. Failed to recalculate.", "corners": corners}
            
            # State 3: User is on the path and not at the end. This is the main navigation state.
            else:
                try:
                    current_index = self.current_path.index(self.current_location.location_id)
                    if current_index + 1 < len(self.current_path):
                        next_waypoint_id = self.current_path[current_index + 1]
                        next_waypoint_info = self.guidance.location_database.get(next_waypoint_id)
                        
                        if next_waypoint_info:
                            target_azimuth = self.guidance._calculate_bearing(self.current_location.coordinates, next_waypoint_info['coordinates'])
                            distance_meters = math.sqrt(
                                (next_waypoint_info['coordinates'][0] - self.current_location.coordinates[0])**2 +
                                (next_waypoint_info['coordinates'][1] - self.current_location.coordinates[1])**2
                            )
                            result = {
                                "status": "NAVIGATING",
                                "next_waypoint_name": next_waypoint_info['location_name'],
                                "target_azimuth": target_azimuth,
                                "target_distance": distance_meters,
                                "corners": corners
                            }
                except Exception as e:
                    result = {"status": "ERROR", "message": f"Error during navigation step: {e}"}

        # No matter what happens, a valid result with a correct status key is returned.
        print(f"Python returning status: {result.get('status')}")
        return result