import os
import logging
from typing import List, Dict, Any
import qrcode
from map_building import BuildingMap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QRGenerator:
    def __init__(self, output_dir: str = "./qr_codes"):
        """
        Initialize QRGenerator with an output directory for QR code images.
        
        Args:
            output_dir (str): Directory to save QR code images.
        """
        self.building_map = BuildingMap()
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        self.color_options = ["red", "green", "blue"]  # Define color options
        self.location_database = self._build_location_database()

    def _build_location_database(self) -> Dict[str, Dict[str, Any]]:
        """
        Build a location database from BuildingMap data.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of location data with location_id as key.
        """
        location_database = {}
        all_locations = self.building_map.bottom_rooms + self.building_map.top_rooms + self.building_map.special_areas
        for i, loc in enumerate(all_locations):
            loc_id = loc['location_id']
            if loc_id not in self.building_map.nodes:
                logger.warning(f"Location {loc_id} not found in nodes")
                continue
            # Assign a color cyclically (red, green, blue)
            color = self.color_options[i % len(self.color_options)]
            location_database[loc_id] = {
                'location_id': loc_id,
                'location_name': loc['name'],
                'qr_orientation': loc.get('qr_orientation', 0.0),
                'coordinates': self.building_map.nodes[loc_id],
                'color': color
            }
        return location_database

    def generate_qr_code(self, location_id: str) -> bool:
        """
        Generate a QR code for a single location and save it as a PNG.
        
        Args:
            location_id (str): The location ID to encode in the QR code.
        
        Returns:
            bool: True if QR code was generated successfully, False otherwise.
        """
        if location_id not in self.location_database:
            logger.error(f"Location {location_id} not found in location database")
            return False
        
        location = self.location_database[location_id]
        # Encode location_id, qr_orientation, and color
        qr_data = f"{location['location_id']}|{location['qr_orientation']}|{location['color']}"
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Use colored QR code based on location color
            fill_color = location['color']
            qr_image = qr.make_image(fill_color=fill_color, back_color="white")
            output_path = os.path.join(self.output_dir, f"{location_id}.png")
            qr_image.save(output_path)
            logger.info(f"Generated QR code for {location_id} ({location['color']}) at {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate QR code for {location_id}: {e}")
            return False

    def generate_all_qr_codes(self) -> List[str]:
        """
        Generate QR codes for all locations in the location database.
        
        Returns:
            List[str]: List of location IDs for which QR codes were successfully generated.
        """
        success_ids = []
        for location_id in self.location_database:
            if self.generate_qr_code(location_id):
                success_ids.append(location_id)
        return success_ids

if __name__ == "__main__":
    # Example usage for testing
    qr_generator = QRGenerator(output_dir="./qr_codes")
    success_ids = qr_generator.generate_all_qr_codes()
    print(f"Generated QR codes for: {success_ids}")
