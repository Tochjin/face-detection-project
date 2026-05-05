import os
import cv2
import time
import pandas as pd
from pathlib import Path
from ultralytics import YOLO
from deepface import DeepFace

from database import add_user, find_closest_user, setup_database, SessionLocal, User, FaceEmbedding, AccessLog

DATASET_ROOT = Path("data/CFP")
GALLERY_DIR = DATASET_ROOT / "gallery"
PROBES_GENUINE_DIR = DATASET_ROOT / "probes" / "genuine"
PROBES_IMPOSTOR_DIR = DATASET_ROOT / "probes" / "impostor"
OUTPUT_CSV = "cfp_results.csv"

# Load YOLO
try:
    yolo_model = YOLO("models/best.pt")
except Exception as e:
    print("Failed to load YOLO model. Please ensure models/best.pt is in the project root.")
    exit(1)

def cleanup_db():
    print("Cleaning up old Test users from database...")
    session = SessionLocal()
    users = session.query(User).filter(User.faculty == 'Test_CFP').all()
    count = 0
    for u in users:
        session.query(FaceEmbedding).filter(FaceEmbedding.user_id == u.id).delete()
        session.query(AccessLog).filter(AccessLog.user_id == u.id).delete(synchronize_session=False)
        session.delete(u)
        count += 1
    session.commit()
    print(f"Cleaned up {count} old test users.")

def enroll_gallery():
    print("Enrolling authorized users from Gallery...")
    enrolled_count = 0
    for person_dir in GALLERY_DIR.iterdir():
        if not person_dir.is_dir(): continue
        
        person_id = person_dir.name
        img_files = sorted(list(person_dir.glob("*.jpg")))
        if not img_files: continue
        
        embeddings_dict = {}
        
        for img_file in img_files:
            img = cv2.imread(str(img_file))
            if img is None: continue
            
            # Detect face with YOLO
            results = yolo_model(img, verbose=False)
            if len(results[0].boxes) > 0:
                box = results[0].boxes[0].xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = box
                x1, y1 = max(0, x1), max(0, y1)
                
                cropped = img[y1:y2, x1:x2]
                if cropped.size > 0:
                    try:
                        df_res = DeepFace.represent(img_path=cropped, model_name="Facenet512", enforce_detection=False, detector_backend="skip")
                        if df_res:
                            # Use filename as angle key (e.g. "frontal_01", "profile_01")
                            angle_key = img_file.stem  # e.g. "frontal_01"
                            embeddings_dict[angle_key] = df_res[0]["embedding"]
                    except Exception as e:
                        pass
        
        if embeddings_dict:
            add_user(
                user_id=person_id,
                user_name=f"Subject_{person_id}",
                gender="Unknown",
                faculty="Test_CFP",
                department="Evaluation",
                embeddings_dict=embeddings_dict
            )
            enrolled_count += 1
    print(f"Enrolled {enrolled_count} users into PostgreSQL ({len(img_files)} images each).")

def evaluate_probes():
    print("Starting Evaluation of Probes...")
    results_log = []
    
    probe_files = []
    # Gather genuine
    for f in PROBES_GENUINE_DIR.glob("*.jpg"):
        probe_files.append((f, True)) # Path, IsGenuine
        
    # Gather impostor
    for f in PROBES_IMPOSTOR_DIR.glob("*.jpg"):
        probe_files.append((f, False))
        
    print(f"Processing {len(probe_files)} probe images...")
    
    for i, (probe_path, is_genuine) in enumerate(probe_files):
        img = cv2.imread(str(probe_path))
        if img is None: continue
        
        start_time = time.time()
        
        # The filename is prefixed with the true ID: "Name___image.jpg"
        true_id = probe_path.name.split("___")[0]
        is_profile = "profile" in probe_path.name
        
        predicted_id = "Unknown"
        distance = 1.0
        
        results = yolo_model(img, verbose=False)
        if len(results[0].boxes) > 0:
            box = results[0].boxes[0].xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = box
            x1, y1 = max(0, x1), max(0, y1)
            cropped = img[y1:y2, x1:x2]
            
            if cropped.size > 0:
                try:
                    df_res = DeepFace.represent(img_path=cropped, model_name="Facenet512", enforce_detection=False, detector_backend="skip")
                    if df_res:
                        embedding = df_res[0]["embedding"]
                        # Search DB - threshold 1.0 to get nearest raw distance
                        match = find_closest_user(embedding, threshold=1.0)
                        if match and match["user_name"].startswith("Subject_"):
                            predicted_id = match["user_name"].replace("Subject_", "")
                            distance = match["distance"]
                except Exception as e:
                    pass
                    
        latency = (time.time() - start_time) * 1000
        
        results_log.append({
            "image": probe_path.name,
            "true_id": true_id,
            "is_genuine": is_genuine,
            "is_profile": is_profile,
            "predicted_id": predicted_id,
            "distance": distance,
            "latency_ms": latency
        })
        
        if i > 0 and i % 100 == 0:
            print(f"Processed {i}/{len(probe_files)} probes...")
            
    df = pd.DataFrame(results_log)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Evaluation complete. Results saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    setup_database()
    # cleanup_db()
    # enroll_gallery()
    evaluate_probes()
