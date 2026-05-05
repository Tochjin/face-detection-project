import os
import cv2
import time
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
from deepface import DeepFace
import numpy as np

# Adjust imports to match your project structure
from database import add_user, find_closest_user, setup_database
from ultralytics import YOLO

# --- Configuration ---
DATASET_ROOT = Path("data/ChokePoint")
SEQUENCE_NAME = "P2E_S1_C1"
SEQUENCE_DIR = DATASET_ROOT / "data" / "P2E_S1_C1"
GROUNDTRUTH_FILES = [
    DATASET_ROOT / "groundtruth" / "groundtruth" / "P2E_S1_C1.1.xml",
    DATASET_ROOT / "groundtruth" / "groundtruth" / "P2E_S1_C1.2.xml"
]
GALLERY_DIR = DATASET_ROOT / "gallery" # You should create this and put 25 identities inside

OUTPUT_CSV = "chokepoint_results.csv"

# --- Models ---
# Load YOLO model
print("Loading YOLO model...")
try:
    yolo_model = YOLO("models/best.pt")
except Exception as e:
    print(f"Error loading YOLO: {e}")
    yolo_model = YOLO("yolov8n.pt") # Fallback

def enroll_gallery():
    """
    Reads the gallery directory and enrolls subjects into PostgreSQL.
    Expects structure: gallery/0001/img1.jpg, gallery/0002/img1.jpg, etc.
    """
    print("--- Phase 1: Enrolling Gallery ---")
    if not GALLERY_DIR.exists():
        print(f"Please create {GALLERY_DIR} and place subject folders inside.")
        return

    subject_dirs = [d for d in GALLERY_DIR.iterdir() if d.is_dir()]
    for subject_dir in subject_dirs:
        subject_id = subject_dir.name
        img_paths = list(subject_dir.glob("*.jpg"))
        
        if not img_paths:
            continue
            
        print(f"Enrolling {subject_id}...")
        try:
            # For simplicity, we just take the first image as 'front' angle
            img_path = str(img_paths[0])
            
            df_results = DeepFace.represent(
                img_path=img_path, 
                model_name="Facenet512", 
                enforce_detection=True,
                detector_backend="mtcnn"
            )
            
            if df_results:
                embedding = df_results[0]["embedding"]
                embeddings_dict = {"front": embedding}
                
                # Insert into DB
                add_user(
                    user_id=subject_id,
                    user_name=f"Subject_{subject_id}",
                    gender="Unknown",
                    faculty="Test",
                    department="Test",
                    embeddings_dict=embeddings_dict
                )
        except Exception as e:
            print(f"Failed to enroll {subject_id}: {e}")

def get_groundtruth():
    """
    Parses the ChokePoint XML groundtruth to know who is actually in each frame.
    Returns a dictionary mapping frame_number -> list of person_ids.
    """
    gt_map = {}
    for gt_file in GROUNDTRUTH_FILES:
        if not gt_file.exists():
            print(f"Groundtruth file {gt_file} not found. Skipping...")
            continue
            
        tree = ET.parse(gt_file)
        root = tree.getroot()
        
        for frame in root.findall('frame'):
            frame_num = int(frame.attrib['number'])
            persons = []
            for person in frame.findall('person'):
                persons.append(person.attrib['id'])
            gt_map[frame_num] = persons
    return gt_map

def calculate_iou(boxA, boxB):
    # Determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    # Compute the area of intersection
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)

    # Compute the area of both bounding boxes
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

    # Compute the intersection over union
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def process_video_sequence():
    """
    Iterates through the frames of the sequence and performs the evaluation.
    """
    print("--- Phase 2 & 4: Processing Video & Stress Test ---")
    if not SEQUENCE_DIR.exists():
        print(f"Sequence directory not found: {SEQUENCE_DIR}")
        return

    frames = sorted(list(SEQUENCE_DIR.glob("*.jpg")))
    gt_map = get_groundtruth()
    
    results_log = []
    
    # Simple Centroid/Box Tracker
    # Maps track_id -> {"box": [x1,y1,x2,y2], "identified": False, "name": None, "distance": None}
    active_tracks = {}
    next_track_id = 0
    
    total_start_time = time.time()
    # Process each frame
    for frame_idx, frame_path in enumerate(frames):
        try:
            frame_num = int(frame_path.stem)
        except ValueError:
            frame_num = frame_idx
            
        img = cv2.imread(str(frame_path))
        if img is None:
            continue
            
        start_time = time.time()
        
        # 1. Detection
        yolo_results = yolo_model(img, verbose=False)
        detected_boxes = []
        
        for result in yolo_results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                if conf >= 0.5:
                    detected_boxes.append([x1, y1, x2, y2])
                    
        # 2. Tracking Update (Simple IoU based)
        new_active_tracks = {}
        for box in detected_boxes:
            best_iou = 0
            best_track_id = None
            
            for t_id, t_info in active_tracks.items():
                iou = calculate_iou(box, t_info["box"])
                if iou > best_iou and iou > 0.3: # Threshold for tracking
                    best_iou = iou
                    best_track_id = t_id
            
            if best_track_id is not None:
                new_active_tracks[best_track_id] = active_tracks[best_track_id]
                new_active_tracks[best_track_id]["box"] = box
            else:
                new_active_tracks[next_track_id] = {"box": box, "identified": False, "name": "Unknown", "distance": 1.0}
                next_track_id += 1
                
        active_tracks = new_active_tracks
        
        # 3. Identification
        for t_id, t_info in active_tracks.items():
            if not t_info["identified"]:
                x1, y1, x2, y2 = t_info["box"]
                h, w = img.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                cropped = img[y1:y2, x1:x2]
                
                if cropped.size > 0 and cropped.shape[0] >= 30 and cropped.shape[1] >= 30:
                    try:
                        # Extract embedding
                        df_results = DeepFace.represent(
                            img_path=cropped, 
                            model_name="Facenet512", 
                            enforce_detection=False,
                            detector_backend="skip"
                        )
                        
                        if df_results:
                            embedding = df_results[0]["embedding"]
                            
                            # Search DB - set threshold to 1.0 just to get nearest, we'll filter later
                            match = find_closest_user(embedding, threshold=1.0)
                            
                            if match:
                                t_info["name"] = match["user_name"].replace("Subject_", "")
                                t_info["distance"] = match["distance"]
                                # Only lock in identity if it's very confident, otherwise keep trying
                                if match["distance"] < 0.5: 
                                    t_info["identified"] = True
                    except Exception as e:
                        pass # Face too small or MTCNN failed
                        
            # 4. Logging
            end_time = time.time()
            latency = (end_time - start_time) * 1000 # ms
            
            ground_truth_ids = gt_map.get(frame_num, [])
            
            results_log.append({
                "frame": frame_num,
                "track_id": t_id,
                "predicted_id": t_info["name"],
                "distance": t_info["distance"],
                "ground_truth_ids": ",".join(ground_truth_ids),
                "latency_ms": latency
            })
            
        if frame_idx % 50 == 0:
            print(f"Processed frame {frame_num} ({frame_idx}/{len(frames)})")

    total_time = time.time() - total_start_time
    fps = len(frames) / total_time
    print(f"--- Stress Test Complete ---")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Average FPS: {fps:.2f}")

    # Save to CSV
    df = pd.DataFrame(results_log)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved evaluation results to {OUTPUT_CSV}")

if __name__ == "__main__":
    setup_database() # Ensure DB is ready
    # Uncomment to run enrollment
    enroll_gallery()
    process_video_sequence()
