import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import threading
import os

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.process_video import process_video

class VideoProcessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ประมวลผลวิดีโอ (Video Processing)")
        self.root.geometry("600x400")
        self.root.configure(padx=30, pady=30)
        
        self.input_file = ""
        self.output_file = ""
        
        self.create_widgets()

    def create_widgets(self):
        # Title
        tk.Label(self.root, text="ระบบวิเคราะห์วิดีโอย้อนหลัง", font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Input Frame
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(input_frame, text="1. เลือกวิดีโอต้นฉบับ:", font=("Arial", 12)).pack(anchor="w")
        
        in_btn_frame = tk.Frame(input_frame)
        in_btn_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_input = tk.Label(in_btn_frame, text="ยังไม่ได้เลือกไฟล์", fg="gray", font=("Arial", 10), bg="#f0f0f0", width=50, anchor="w", padx=5)
        self.lbl_input.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(in_btn_frame, text="เลือกไฟล์ (Browse)", command=self.browse_input, bg="#2196F3", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

        # Output Frame
        output_frame = tk.Frame(self.root)
        output_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(output_frame, text="2. เลือกที่บันทึกไฟล์วิดีโอ:", font=("Arial", 12)).pack(anchor="w")
        
        out_btn_frame = tk.Frame(output_frame)
        out_btn_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_output = tk.Label(out_btn_frame, text="ยังไม่ได้เลือกที่บันทึก", fg="gray", font=("Arial", 10), bg="#f0f0f0", width=50, anchor="w", padx=5)
        self.lbl_output.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(out_btn_frame, text="บันทึกที่ (Save As)", command=self.browse_output, bg="#2196F3", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

        # Progress and Action
        action_frame = tk.Frame(self.root)
        action_frame.pack(fill=tk.X, pady=30)
        
        self.btn_process = tk.Button(action_frame, text="▶ เริ่มประมวลผล (Start Processing)", command=self.start_processing, bg="#4CAF50", fg="white", font=("Arial", 14, "bold"), width=30)
        self.btn_process.pack(pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(action_frame, orient="horizontal", mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))
        
        self.lbl_progress = tk.Label(action_frame, text="พร้อมทำงาน (Ready)", font=("Arial", 10))
        self.lbl_progress.pack()

    def browse_input(self):
        file_path = filedialog.askopenfilename(
            title="เลือกไฟล์วิดีโอ",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*")]
        )
        if file_path:
            self.input_file = file_path
            filename = os.path.basename(file_path)
            self.lbl_input.config(text=filename, fg="black")
            
            # Auto-suggest output name
            if not self.output_file:
                dir_name = os.path.dirname(file_path)
                name, ext = os.path.splitext(filename)
                suggested_out = os.path.join(dir_name, f"{name}_processed{ext}")
                self.output_file = suggested_out
                self.lbl_output.config(text=os.path.basename(suggested_out), fg="black")

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="บันทึกไฟล์วิดีโอ (Save As)",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if file_path:
            self.output_file = file_path
            self.lbl_output.config(text=os.path.basename(file_path), fg="black")

    def start_processing(self):
        if not self.input_file:
            messagebox.showwarning("Warning", "กรุณาเลือกไฟล์วิดีโอต้นฉบับก่อน")
            return
        if not self.output_file:
            messagebox.showwarning("Warning", "กรุณาเลือกที่อยู่ในการบันทึกไฟล์")
            return

        # Update UI state
        self.btn_process.config(state=tk.DISABLED, text="กำลังทำงาน... (Processing)")
        self.progress_var.set(0)
        self.lbl_progress.config(text="กำลังวิเคราะห์และโหลดข้อมูลรอก่อนสักครู่...")
        
        # Start processing in a separate thread so GUI doesn't freeze
        thread = threading.Thread(target=self.run_processing_thread)
        thread.daemon = True
        thread.start()

    def run_processing_thread(self):
        def update_progress(current, total):
            # Calculate percentage
            percentage = (current / total) * 100 if total > 0 else 0
            
            # Use root.after to update tkinter safely from a thread
            self.root.after(0, self._update_ui_progress, current, total, percentage)
            
        success = process_video(self.input_file, self.output_file, progress_callback=update_progress)
        
        # When finished
        self.root.after(0, self._processing_finished, success)

    def _update_ui_progress(self, current, total, percentage):
        self.progress_var.set(percentage)
        self.lbl_progress.config(text=f"กำลังประมวลผล... {int(percentage)}% ({current}/{total} เฟรม)")

    def _processing_finished(self, success):
        self.btn_process.config(state=tk.NORMAL, text="▶ เริ่มประมวลผล (Start Processing)")
        if success:
            self.progress_var.set(100)
            self.lbl_progress.config(text="เสร็จสมบูรณ์! (Completed!)")
            messagebox.showinfo("Success", "การประมวลผลวิดีโอเสร็จสมบูรณ์!")
        else:
            self.lbl_progress.config(text="เกิดข้อผิดพลาด (Error)")
            messagebox.showerror("Error", "เกิดข้อผิดพลาดในการประมวลผล กรุณาตรวจสอบ Console")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessApp(root)
    root.mainloop()
