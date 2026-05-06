from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import cv2
import threading
import time
from ultralytics import YOLO
from pathlib import Path
import sys
import numpy as np
from deepface import DeepFace

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.database import setup_database, log_user_access, add_user, get_all_users, delete_user
from src.detector import FaceDetector

app = FastAPI()

# Mount the static frontend folder
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web")), name="static")

MODEL_PATH = BASE_DIR / 'models' / 'best.pt'
if not MODEL_PATH.exists():
    print(f"Error: Model not found at {MODEL_PATH}")

import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"YOLO is using device: {device}")

model = YOLO(str(MODEL_PATH)).to(device)
detector = FaceDetector(model)

# Video capture and processing globals
cap = None
latest_frame = None
latest_logs = []
log_lock = threading.Lock()
COOLDOWN_MS = 5000
log_cooldown = {}

camera_active = True

def process_video_stream():
    global cap, latest_frame, camera_active
    
    while True:
        if not camera_active:
            if cap is not None:
                cap.release()
                cap = None
                latest_frame = None
            time.sleep(0.5)
            continue
            
        if cap is None:
            cap = cv2.VideoCapture(0)
            
        if not cap.isOpened():
            time.sleep(0.5)
            continue
            
        # Flush the buffer to avoid accumulated delay from heavy DeepFace processing
        for _ in range(4):
            cap.grab()
            
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue
            
        # Process frame through YOLO + DeepFace
        try:
            annotated_frame, person_info = detector.process_frame(frame)
            
            # Handle logging
            if person_info is not None:
                user_id = person_info['id']
                user_name = person_info['user_name']
                now = time.time() * 1000
                
                with log_lock:
                    if user_id not in log_cooldown or (now - log_cooldown[user_id] > COOLDOWN_MS):
                        log_cooldown[user_id] = now
                        log_user_access(user_id)
                        
                        # Add to latest logs for the frontend
                        latest_logs.insert(0, {
                            "id": user_id, 
                            "name": user_name, 
                            "time": time.strftime("%H:%M:%S"),
                            "image": person_info.get("image_base64")
                        })
                        if len(latest_logs) > 20:
                            latest_logs.pop()
                            
        except Exception as e:
            print("Detection error:", e)
            annotated_frame = frame

        # Encode for streaming
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if ret:
            latest_frame = buffer.tobytes()

# Start background thread for video processing
@app.on_event("startup")
def startup_event():
    setup_database()
    threading.Thread(target=process_video_stream, daemon=True).start()

@app.on_event("shutdown")
def shutdown_event():
    global cap
    if cap is not None:
        cap.release()

def generate_frames():
    global latest_frame
    while True:
        if latest_frame is None:
            time.sleep(0.1)
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        time.sleep(0.03) # Limit to ~30 FPS

from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/camera/status")
def get_camera_status():
    global camera_active
    return {"camera_active": camera_active}

@app.post("/api/camera/toggle")
async def toggle_camera(state: str = Form(...)):
    global camera_active
    camera_active = (state.lower() == 'true')
    return {"status": "ok", "camera_active": camera_active}

@app.get("/api/logs")
def get_recent_logs():
    with log_lock:
        return JSONResponse(content=latest_logs)

@app.get("/api/users")
def api_get_users():
    users = get_all_users()
    return JSONResponse(content=[{"id": u["id"], "name": u["user_name"]} for u in users])

@app.delete("/api/users/{user_id}")
def api_delete_user(user_id: str):
    success = delete_user(user_id)
    if success:
        return {"message": "User deleted"}
    return JSONResponse(content={"detail": "Failed to delete user"}, status_code=500)

@app.post("/api/register")
async def register_user(
    id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    faculty: str = Form(...),
    department: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # Read uploaded image
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Resize to prevent MTCNN memory issues
        max_size = 1000
        height, width = img.shape[:2]
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)))

        # Extract features using DeepFace (from detector.py logic)
        results = DeepFace.represent(img, model_name="Facenet512", enforce_detection=False, detector_backend="mtcnn")
        
        if not results:
            return JSONResponse(content={"detail": "No face found in image"}, status_code=400)
            
        embedding = results[0]["embedding"]
        embeddings_dict = {"front": embedding} # We just save front for now

        # Save to DB
        success = add_user(id, name, gender, faculty, department, embeddings_dict)
        if success:
            return {"message": "Registration successful"}
        else:
            return JSONResponse(content={"detail": "Database error"}, status_code=500)

    except Exception as e:
        print("Registration error:", e)
        return JSONResponse(content={"detail": str(e)}, status_code=500)
