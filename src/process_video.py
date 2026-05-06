import cv2
from ultralytics import YOLO
from pathlib import Path
import sys
import argparse

# Add src to python path so we can import modules
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.database import setup_database, log_user_access
from src.detector import FaceDetector

MODEL_PATH = BASE_DIR / 'models' / 'best.pt'

def process_video(input_video_path, output_video_path, progress_callback=None):
    print("Setting up database and loading model...")
    setup_database()
    
    try:
        # 1. Load the YOLO model
        if not MODEL_PATH.exists():
            print(f"Error: Model not found at {MODEL_PATH}")
            return False
            
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"YOLO is using device: {device}")
        
        model = YOLO(str(MODEL_PATH)).to(device) 
        detector = FaceDetector(model)

        # 2. Open the input video
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            print(f"Error: Cannot open video file {input_video_path}")
            return False

        # Get video properties for output
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        if original_fps == 0 or original_fps != original_fps: # Handle 0 or NaN
            original_fps = 30.0
            
        target_fps = 5.0
        process_interval = max(1, int(round(original_fps / target_fps)))
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Define codec and create VideoWriter object with target FPS (5fps)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec for .mp4 format
        out = cv2.VideoWriter(output_video_path, fourcc, target_fps, (width, height))

        print(f"Processing video: {input_video_path}")
        print(f"Original FPS: {original_fps:.2f} -> Output will be saved at {target_fps} fps (Processing 1 every {process_interval} frames)")
        print(f"Output will be saved to: {output_video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        processed_count = 0

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
                
            frame_count += 1
            
            # Skip frames to achieve 5 FPS
            if frame_count % process_interval != 0:
                # We still update the progress bar for skipped frames
                if progress_callback is not None:
                    progress_callback(frame_count, total_frames)
                continue

            # 3. Run detection and recognition only on interval frames
            annotated_frame, person_info = detector.process_frame(frame)

            # 4. Write the frame into the output video
            out.write(annotated_frame)
            processed_count += 1
            
            # Print progress
            print(f"Read frame {frame_count} / {total_frames} | Saved {processed_count} frames", end='\r')
            
            if progress_callback is not None:
                progress_callback(frame_count, total_frames)

        print(f"\nFinished processing {frame_count} frames.")
        print(f"Output successfully saved to {output_video_path}")

        # Clean up
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print("\nAn error occurred:", e)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a video to perform face detection and recognition.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input video file (e.g., test.mp4)")
    parser.add_argument("-o", "--output", required=True, help="Path to save the processed output video file (e.g., output.mp4)")
    
    args = parser.parse_args()
    process_video(args.input, args.output)
