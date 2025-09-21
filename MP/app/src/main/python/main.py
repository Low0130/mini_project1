# main.py — Integrate all modules and provide simple CLI for testing
import os
import time
import argparse

import cv2

# assumed filenames (如果你的文件名不同请改成对应名字)
from qr_generator import QRGenerator
from map_building import BuildingMap
from qr_detection import QRDetectionModule, QRColor
from qr_decoder import QRDecoder
from route_guidance import RouteGuidance

def generate_qr_and_map():
    print("Generating QR codes into ./qr_codes ...")
    gen = QRGenerator(output_dir="./qr_codes")
    ids = gen.generate_all_qr_codes()
    print(f"Generated {len(ids)} QR codes: {ids}")
    print("Saving map image map.png ...")
    bm = BuildingMap()
    bm.plot_map(filename="map.png")
    print("map.png saved.")

def detect_only():
    detector = QRDetectionModule(target_color=QRColor.ANY)
    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit, 'c' to try capture nearest QR for decode.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break
        # show annotated frame (process_frame internally resizes)
        annotated, text, voice = detector.process_frame(frame)
        cv2.putText(annotated, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        cv2.imshow("QR Detect Only", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            # try to get nearest and print info
            resized = cv2.resize(frame, (detector.frame_width, detector.frame_height))
            targets = detector.detect_qr_codes(resized)
            nearest = detector.get_nearest_qr(targets)
            if nearest:
                print("Nearest QR:", nearest)
            else:
                print("No QR detected right now.")
    cap.release()
    cv2.destroyAllWindows()

def simulate_images():
    detector = QRDetectionModule(target_color=QRColor.ANY)
    decoder = QRDecoder()
    folder = "./qr_codes"
    if not os.path.exists(folder):
        print("No './qr_codes' directory found. Run generate first.")
        return
    imgs = [f for f in os.listdir(folder) if f.lower().endswith(('.png','.jpg','.jpeg'))]
    print(f"Found {len(imgs)} images. Trying decode each.")
    for fn in imgs:
        path = os.path.join(folder, fn)
        img = cv2.imread(path)
        if img is None:
            print("Failed load", path)
            continue
        resized = cv2.resize(img, (detector.frame_width, detector.frame_height))
        targets = detector.detect_qr_codes(resized)
        nearest = detector.get_nearest_qr(targets)
        if nearest:
            loc = decoder.read_qr_code(nearest, resized)
            print(f"{fn} -> detected nearest size {nearest.width}x{nearest.height}, decode -> {getattr(loc,'location_id', None)}")
        else:
            print(f"{fn} -> no QR detected")

def live_navigation():
    detector = QRDetectionModule(target_color=QRColor.ANY)
    decoder = QRDecoder()
    guidance = RouteGuidance(output_dir="./output")
    cap = cv2.VideoCapture(0)
    print("Live navigation: scan a nearby QR to establish current location.")
    print("Press 'q' to quit. Press 'c' to attempt decode current nearest QR.")

    current_location_id = None
    # Stage 1: find initial location by scanning until decoder returns a LocationInfo
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break
        resized = cv2.resize(frame, (detector.frame_width, detector.frame_height))
        targets = detector.detect_qr_codes(resized)
        nearest = detector.get_nearest_qr(targets)
        annotated, text, voice = detector.process_frame(frame)
        cv2.putText(annotated, "Press 'c' to capture -> decode", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        cv2.imshow("Live Nav - Scan start", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return
        if key == ord('c') and nearest is not None:
            loc = decoder.read_qr_code(nearest, resized)
            if loc:
                current_location_id = loc.location_id
                print(f"Current location: {loc.location_name} ({current_location_id})")
                break
            else:
                print("Decode failed - try again or move closer.")
    # Ask for destination
    print("Choose destination from the list below (enter location_id). You can copy-paste.")
    for lid, info in guidance.location_database.items():
        print(f" - {lid}: {info['location_name']}")
    dest = input("Enter destination location_id (or leave blank to cancel): ").strip()
    if not dest:
        print("No destination entered. Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        return
    nav_data = guidance.prepare_navigation_data(current_location_id, dest)
    if not nav_data:
        print("Failed to prepare navigation (no path?). Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        return
    path = nav_data["path"]
    print("Computed path:", " -> ".join(path))
    print("map saved to ./output/map.png")

    # Step through path: user will walk and scan next QR when reach it
    for next_node in path[1:]:
        print(f"\nNext target: {next_node} ({guidance.location_database[next_node]['location_name']})")
        print("Instruction: Please move toward the next landmark. When you reach it, point camera to its QR and press 'c' to scan.")
        reached = False
        while not reached:
            ret, frame = cap.read()
            if not ret:
                print("Camera read failed")
                break
            annotated, text, voice = detector.process_frame(frame)
            cv2.putText(annotated, f"Target: {next_node} - press 'c' to capture", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            cv2.imshow("Live Nav - Follow Path", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
            if key == ord('c'):
                resized = cv2.resize(frame, (detector.frame_width, detector.frame_height))
                targets = detector.detect_qr_codes(resized)
                nearest = detector.get_nearest_qr(targets)
                if nearest:
                    loc = decoder.read_qr_code(nearest, resized)
                    if loc:
                        print(f"Scanned: {loc.location_id} ({loc.location_name})")
                        if loc.location_id == next_node:
                            print("Arrived at expected next node.")
                            current_location_id = loc.location_id
                            reached = True
                        else:
                            print("Scanned a different node. If you are not there yet, continue walking to the correct one.")
                    else:
                        print("Decode failed. Try again (move closer / better angle).")
                else:
                    print("No QR found in frame. Try again (point camera at QR).")
        # loop continues to next node
    print("\nDestination reached. Navigation complete.")
    cap.release()
    cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description="Integration main for QR navigation system")
    parser.add_argument("mode", choices=["generate","detect","simulate","live"], help="mode: generate/detect/simulate/live")
    args = parser.parse_args()
    if args.mode == "generate":
        generate_qr_and_map()
    elif args.mode == "detect":
        detect_only()
    elif args.mode == "simulate":
        simulate_images()
    elif args.mode == "live":
        live_navigation()

if __name__ == "__main__":
    main()
