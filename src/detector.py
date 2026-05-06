import cv2
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"DeepFace (TensorFlow) found GPUs: {len(gpus)}. Enabling memory growth.")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(f"TensorFlow memory growth error: {e}")
else:
    print("DeepFace (TensorFlow) is using CPU.")

from deepface import DeepFace
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
from src.database import find_closest_user

class FaceDetector:
    def __init__(self, yolo_model):
        self.model = yolo_model

    def process_frame(self, frame):
        """
        Run YOLO detection and DeepFace representation on a single frame.
        Searches PostgreSQL for the closest face embedding.
        Returns the annotated frame and the metadata of the last recognized person.
        """
        results = self.model(frame)
        person_info = None # Holds a dict of user info if matched
        
        for result in results:
            boxes = result.boxes 
            
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                confidence = float(box.conf[0])

                if confidence < 0.5:
                    continue

                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                cropped_img = frame[y1:y2, x1:x2]
                
                person_name = "Unknown"

                if cropped_img.size != 0:
                    try:
                        # 1. Extract Face Vector
                        df_results = DeepFace.represent(
                            img_path=cropped_img, 
                            model_name="Facenet512", 
                            enforce_detection=False,
                            detector_backend="skip"
                        )
                        
                        if df_results:
                            embedding = df_results[0]["embedding"]
                            
                            # 2. Search PostgreSQL Vector Database (threshold 0.35)
                            matched_user = find_closest_user(embedding, threshold=0.40)
                            
                            if matched_user:
                                person_info = matched_user
                                distance_val = round(matched_user["distance"], 2)
                                angle = matched_user.get("matched_angle", "front")
                                person_name = f"{matched_user['user_name']} [{angle}] ({distance_val})"
                    except Exception as e:
                        print("Vector DB Search Error:", e)

                # Draw the bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw text background
                (text_w, text_h), _ = cv2.getTextSize(person_name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x1, y1 - 25), (x1 + text_w, y1), (0, 255, 0), -1)

                # Draw text
                cv2.putText(frame, person_name, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                
        return frame, person_info
