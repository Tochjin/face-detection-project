import cv2
from ultralytics import YOLO
from pathlib import Path
import sys

# Add src to python path so we can import modules
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

# We removed get_user_info because person_info is returned directly by detector
from src.database import setup_database, log_user_access
from src.detector import FaceDetector

MODEL_PATH = BASE_DIR / 'models' / 'best.pt'

def main():
    # Setup database
    setup_database()
    
    try:
        # 1. Load the YOLO model
        if not MODEL_PATH.exists():
            print(f"Error: Model not found at {MODEL_PATH}")
            return
            
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"YOLO is using device: {device}")
        
        model = YOLO(str(MODEL_PATH)).to(device) 
        detector = FaceDetector(model)

        # 2. Open the video stream
        cap = cv2.VideoCapture(1)
        
        # We will hold the info of the last detected person
        last_person_info = None

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Failed to read from stream.")
                break

            # 3. Run detection and recognition
            annotated_frame, person_info = detector.process_frame(frame)
            if person_info is not None:
                last_person_info = person_info

            # 4. Show the main stream
            cv2.imshow("YOLO Live Stream", annotated_frame)

            # Press 'q' to quit the application
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Clean up
        cap.release()
        cv2.destroyAllWindows()

        # Fetch Detailed User Info and Log
        if last_person_info is not None:
            print("\n" + "="*30)
            print(f"ข้อมูลผู้ใช้งาน (User Info):")
            print(f"- รหัส (ID):       {last_person_info['id']}")
            print(f"- ชื่อ (Name):     {last_person_info['user_name']}")
            print(f"- เพศ (Gender):    {last_person_info['gender']}")
            print(f"- คณะ (Faculty):   {last_person_info['faculty']}")
            print(f"- สาขา (Dept):     {last_person_info['department']}")
            print(f"[Match Distance]:  {round(last_person_info['distance'], 2)}")
            print("="*30 + "\n")
            
            # Log to DB
            log_user_access(last_person_info['id'])
        else:
            print("\nไม่มีการตรวจพบใบหน้าผู้ใช้งานที่เป็นที่รู้จัก (No known user detected)\n")
            log_user_access("ไม่พบผู้ใช้")
        
    except Exception as e:
        print("เกิดข้อผิดพลาด:", e)

if __name__ == "__main__":
    main()
