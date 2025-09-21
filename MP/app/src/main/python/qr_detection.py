"""
QR Code Detection Module for Visually Impaired Navigation System
================================================================
Module A: QR Code Detection with Color Recognition and Guidance
For Android deployment using Pydroid3 or Kivy
"""
#!/usr/bin/env python3
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
from typing import Tuple, Optional, List
import math
from dataclasses import dataclass
from enum import Enum

# Configuration for colored QR codes
class QRColor(Enum):
    """Supported QR code colors"""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    ANY = "any"  # Detect any color

@dataclass
class QRTarget:
    """Information about detected QR code"""
    center_x: int
    center_y: int
    width: int
    height: int
    distance_estimate: float  # Estimated distance based on size
    angle_from_center: float  # Angle from screen center
    color: str
    corners: List[Tuple[int, int]]
    
class QRDetectionModule:
    """
    QR Detection Module for VI Navigation
    Detects colored QR codes and provides guidance
    """
    
    def __init__(self, target_color: QRColor = QRColor.ANY):
        """
        Initialize the QR detection module
        
        Args:
            target_color: Color of QR codes to detect (RED, GREEN, BLUE, or ANY)
        """
        self.target_color = target_color
        self.frame_width = 640
        self.frame_height = 480
        self.center_x = self.frame_width // 2
        self.center_y = self.frame_height // 2
        
        # QR code reference size for distance estimation
        # Assume standard QR code is 10cm and appears as 200px at 30cm distance
        self.reference_size = 200  # pixels
        self.reference_distance = 30  # cm
        
        # Color ranges in HSV for detection
        self.color_ranges = {
            QRColor.RED: [
                (0, 70, 50, 10, 255, 255),      # Lower red range
                (170, 70, 50, 180, 255, 255)    # Upper red range
            ],
            QRColor.GREEN: [
                (40, 40, 40, 80, 255, 255)      # Green range
            ],
            QRColor.BLUE: [
                (100, 50, 50, 130, 255, 255)    # Blue range
            ]
        }
        
    def detect_colored_regions(self, frame: np.ndarray, color: QRColor) -> np.ndarray:
        """
        Detect regions of specific color in the frame
        
        Args:
            frame: Input frame
            color: Target color to detect
            
        Returns:
            Mask of detected color regions
        """
        if color == QRColor.ANY:
            return np.ones(frame.shape[:2], dtype=np.uint8) * 255
        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        
        color_ranges = self.color_ranges.get(color, [])
        for range_values in color_ranges:
            if len(range_values) == 6:
                lower = np.array(range_values[:3])
                upper = np.array(range_values[3:])
                mask_part = cv2.inRange(hsv, lower, upper)
                mask = cv2.bitwise_or(mask, mask_part)
        
        # Clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    def detect_qr_codes(self, frame: np.ndarray) -> List[QRTarget]:
        """
        Detect QR codes in the frame
        
        Args:
            frame: Input camera frame
            
        Returns:
            List of detected QR targets
        """
        detected_qrs = []
        
        # Get color mask
        color_mask = self.detect_colored_regions(frame, self.target_color)
        
        # Apply color mask to frame
        masked_frame = cv2.bitwise_and(frame, frame, mask=color_mask)
        
        # Convert to grayscale for QR detection
        gray = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast for better detection
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Try different preprocessing methods
        preprocessed_images = [
            enhanced,
            cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
            cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)
        ]
        
        for processed in preprocessed_images:
            decoded = decode(processed, symbols=[ZBarSymbol.QRCODE])
            
            for qr in decoded:
                # Get corner points
                corners = [(p.x, p.y) for p in qr.polygon]
                
                # Calculate center and size
                x_coords = [p[0] for p in corners]
                y_coords = [p[1] for p in corners]
                center_x = sum(x_coords) // len(x_coords)
                center_y = sum(y_coords) // len(y_coords)
                width = max(x_coords) - min(x_coords)
                height = max(y_coords) - min(y_coords)
                
                # Estimate distance based on QR code size
                avg_size = (width + height) / 2
                distance = self.estimate_distance(avg_size)
                
                # Calculate angle from screen center
                angle = self.calculate_angle_from_center(center_x, center_y)
                
                # Determine actual color of QR code region
                qr_color = self.identify_qr_color(frame, corners)
                
                # Create QRTarget object
                target = QRTarget(
                    center_x=center_x,
                    center_y=center_y,
                    width=width,
                    height=height,
                    distance_estimate=distance,
                    angle_from_center=angle,
                    color=qr_color,
                    corners=corners
                )
                
                # Check if this QR is not a duplicate
                if not self.is_duplicate(target, detected_qrs):
                    detected_qrs.append(target)
            
            # If we found QR codes, stop trying other methods
            if detected_qrs:
                break
        
        return detected_qrs
    
    def estimate_distance(self, qr_size: float) -> float:
        """
        Estimate distance to QR code based on its size in pixels
        
        Args:
            qr_size: Size of QR code in pixels
            
        Returns:
            Estimated distance in cm
        """
        if qr_size <= 0:
            return float('inf')
        
        # Using inverse proportion: distance = (reference_size * reference_distance) / current_size
        distance = (self.reference_size * self.reference_distance) / qr_size
        return distance
    
    def calculate_angle_from_center(self, x: int, y: int) -> float:
        """
        Calculate angle from screen center to point
        
        Args:
            x, y: Point coordinates
            
        Returns:
            Angle in degrees (-180 to 180)
        """
        dx = x - self.center_x
        dy = y - self.center_y
        angle = math.degrees(math.atan2(dx, -dy))  # Negative dy for screen coordinates
        return angle
    
    def identify_qr_color(self, frame: np.ndarray, corners: List[Tuple[int, int]]) -> str:
        """
        Identify the dominant color of QR code region
        
        Args:
            frame: Original frame
            corners: QR code corner points
            
        Returns:
            Color name (red, green, blue, or unknown)
        """
        # Create mask for QR code region
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        pts = np.array(corners, np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], 255)
        
        # Get average color in QR region
        mean_bgr = cv2.mean(frame, mask=mask)[:3]
        b, g, r = mean_bgr

        # Simple color classification based on dominant channel
        if r > g and r > b and r > 100:
            return "red"
        elif g > r and g > b and g > 100:
            return "green"
        elif b > r and b > g and b > 100:
            return "blue"
        else:
            return "unknown"
    
    def is_duplicate(self, target: QRTarget, existing: List[QRTarget], 
                    threshold: int = 50) -> bool:
        """
        Check if target is duplicate of existing detection
        
        Args:
            target: New QR target
            existing: List of existing targets
            threshold: Distance threshold for duplicates
            
        Returns:
            True if duplicate
        """
        for existing_target in existing:
            distance = math.sqrt(
                (target.center_x - existing_target.center_x) ** 2 +
                (target.center_y - existing_target.center_y) ** 2
            )
            if distance < threshold:
                return True
        return False
    
    def get_nearest_qr(self, targets: List[QRTarget]) -> Optional[QRTarget]:
        """
        Get the nearest QR code based on estimated distance
        
        Args:
            targets: List of detected QR targets
            
        Returns:
            Nearest QR target or None
        """
        if not targets:
            return None
        
        return min(targets, key=lambda t: t.distance_estimate)
    
    def generate_guidance(self, target: Optional[QRTarget]) -> Tuple[str, str]:
        """
        Generate guidance instructions for user
        
        Args:
            target: QR target to guide towards
            
        Returns:
            (instruction, voice_instruction) tuple
        """
        if target is None:
            return ("Scanning for QR code...", "No QR code detected. Please rotate slowly.")
        
        instructions = []
        voice_instructions = []
        
        # Distance guidance
        if target.distance_estimate > 100:
            instructions.append(f"QR far: ~{target.distance_estimate:.0f}cm")
            voice_instructions.append("QR code is far. Move forward.")
        elif target.distance_estimate > 50:
            instructions.append(f"QR medium: ~{target.distance_estimate:.0f}cm")
            voice_instructions.append("QR code is at medium distance. Keep moving forward.")
        elif target.distance_estimate > 30:
            instructions.append(f"QR near: ~{target.distance_estimate:.0f}cm")
            voice_instructions.append("QR code is near. Move forward slowly.")
        else:
            instructions.append(f"QR close: ~{target.distance_estimate:.0f}cm")
            voice_instructions.append("QR code is close enough to read.")
        
        # Direction guidance
        if abs(target.angle_from_center) > 30:
            if target.angle_from_center > 0:
                instructions.append("Turn RIGHT")
                voice_instructions.append("Turn right")
            else:
                instructions.append("Turn LEFT")
                voice_instructions.append("Turn left")
        elif abs(target.angle_from_center) > 10:
            if target.angle_from_center > 0:
                instructions.append("Slightly right")
                voice_instructions.append("Turn slightly right")
            else:
                instructions.append("Slightly left")
                voice_instructions.append("Turn slightly left")
        else:
            instructions.append("Centered!")
            voice_instructions.append("QR code is centered")
        
        # Color information
        instructions.append(f"Color: {target.color}")
        
        return (" | ".join(instructions), ". ".join(voice_instructions))
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, str, str]:
        """
        Process a single frame and return annotated frame with guidance
        
        Args:
            frame: Input camera frame
            
        Returns:
            (annotated_frame, text_instruction, voice_instruction)
        """
        # Resize frame for processing
        frame_resized = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        # Detect QR codes
        targets = self.detect_qr_codes(frame_resized)
        
        # Get nearest QR code
        nearest = self.get_nearest_qr(targets)
        
        # Generate guidance
        text_guide, voice_guide = self.generate_guidance(nearest)
        
        # Annotate frame
        annotated = self.annotate_frame(frame_resized, targets, nearest)
        
        return annotated, text_guide, voice_guide
    
    def annotate_frame(self, frame: np.ndarray, targets: List[QRTarget], 
                       nearest: Optional[QRTarget]) -> np.ndarray:
        """
        Draw detection results on frame
        
        Args:
            frame: Input frame
            targets: All detected QR targets
            nearest: Nearest QR target
            
        Returns:
            Annotated frame
        """
        result = frame.copy()
        
        # Draw center crosshair
        cv2.line(result, (self.center_x - 20, self.center_y), 
                (self.center_x + 20, self.center_y), (0, 255, 0), 2)
        cv2.line(result, (self.center_x, self.center_y - 20), 
                (self.center_x, self.center_y + 20), (0, 255, 0), 2)
        
        # Draw all detected QR codes
        for target in targets:
            color = (0, 255, 0) if target == nearest else (0, 128, 255)
            
            # Draw polygon
            pts = np.array(target.corners, np.int32).reshape((-1, 1, 2))
            cv2.polylines(result, [pts], True, color, 2)
            
            # Draw center point
            cv2.circle(result, (target.center_x, target.center_y), 5, color, -1)
            
            # Draw vector from screen center to QR center (only for nearest)
            if target == nearest:
                cv2.arrowedLine(result, (self.center_x, self.center_y),
                              (target.center_x, target.center_y), 
                              (255, 255, 0), 2, tipLength=0.1)
                
                # Add distance label
                label = f"{target.distance_estimate:.0f}cm"
                cv2.putText(result, label, 
                          (target.center_x - 20, target.center_y - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return result

def main():
    """
    Main function for testing the QR detection module
    """
    # Initialize module
    detector = QRDetectionModule(target_color=QRColor.ANY)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("QR Detection Module for VI Navigation")
    print("=====================================")
    print("Commands:")
    print("  'r' - Detect RED QR codes only")
    print("  'g' - Detect GREEN QR codes only")
    print("  'b' - Detect BLUE QR codes only")
    print("  'a' - Detect ANY color QR codes")
    print("  'q' - Quit")
    print()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        annotated, text_guide, voice_guide = detector.process_frame(frame)
        
        # Display guidance on frame
        cv2.rectangle(annotated, (0, 0), (640, 60), (0, 0, 0), -1)
        cv2.putText(annotated, text_guide, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"Mode: {detector.target_color.value}", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show frame
        cv2.imshow('QR Detection for VI', annotated)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            detector.target_color = QRColor.RED
            print("Switched to RED QR detection")
        elif key == ord('g'):
            detector.target_color = QRColor.GREEN
            print("Switched to GREEN QR detection")
        elif key == ord('b'):
            detector.target_color = QRColor.BLUE
            print("Switched to BLUE QR detection")
        elif key == ord('a'):
            detector.target_color = QRColor.ANY
            print("Switched to ANY color QR detection")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()