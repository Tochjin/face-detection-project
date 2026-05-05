import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageTk
from deepface import DeepFace
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.database import setup_database, add_user, get_all_users, delete_user

class RegistrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ระบบลงทะเบียนและจัดการผู้ใช้งาน (User Registration & Management)")
        self.root.geometry("650x850")
        self.root.configure(padx=20, pady=20)
        
        # Make sure DB is ready
        setup_database()

        self.captured_images = {"front": None, "left": None, "right": None}
        
        self.create_widgets()
        self.refresh_user_list()

    def create_widgets(self):
        # Title
        tk.Label(self.root, text="ระบบลงทะเบียนผู้ใช้งาน", font=("Arial", 16, "bold")).pack(pady=10)

        # Form Frame
        form_frame = tk.Frame(self.root)
        form_frame.pack(fill=tk.X, pady=5)

        labels = ["รหัสนักศึกษา/พนักงาน (ID):", "ชื่อผู้ใช้งาน (Name):", "เพศ (Gender):", "คณะ (Faculty):", "สาขา (Department):"]
        self.entries = {}

        for idx, text in enumerate(labels):
            tk.Label(form_frame, text=text, font=("Arial", 12)).grid(row=idx, column=0, sticky="w", pady=5)
            
            if text == "เพศ (Gender):":
                entry = ttk.Combobox(form_frame, values=["ชาย (Male)", "หญิง (Female)", "อี่นๆ (Other)"], font=("Arial", 12))
            else:
                entry = tk.Entry(form_frame, font=("Arial", 12), width=30)
                
            entry.grid(row=idx, column=1, padx=10, pady=5)
            self.entries[text] = entry

        # Image Frame (3 columns for Front, Left, Right)
        img_frame = tk.Frame(self.root)
        img_frame.pack(pady=10)

        self.img_labels = {}
        for idx, angle in enumerate(["front", "left", "right"]):
            col_frame = tk.Frame(img_frame)
            col_frame.grid(row=0, column=idx, padx=5)
            
            lbl_title = tk.Label(col_frame, text=f"ใบหน้า {angle.capitalize()}", font=("Arial", 10, "bold"))
            lbl_title.pack()
            
            img_lbl = tk.Label(col_frame, text=f"No {angle} image", bg="lightgrey", width=25, height=10)
            img_lbl.pack()
            self.img_labels[angle] = img_lbl
            
            # Action Buttons per column
            btn_cam = tk.Button(col_frame, text="📷 ถ่ายกล้อง", command=lambda a=angle: self.capture_from_webcam(a), bg="#4CAF50", fg="white")
            btn_cam.pack(fill=tk.X, pady=2)
            
            btn_file = tk.Button(col_frame, text="📁 เลือกไฟล์", command=lambda a=angle: self.choose_from_file(a), bg="#2196F3", fg="white")
            btn_file.pack(fill=tk.X)

        # Submit Button
        tk.Button(self.root, text="✅ บันทึกข้อมูล (Register)", command=self.register_user, bg="#ff9800", fg="white", font=("Arial", 14, "bold"), width=30).pack(pady=10)

        # --- Management Section ---
        manage_frame = tk.LabelFrame(self.root, text="จัดการผู้ใช้งาน (Manage Users)", font=("Arial", 12, "bold"), padx=10, pady=10)
        manage_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(manage_frame, text="เลือกผู้ใช้งาน (Select User):", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        
        self.user_combobox = ttk.Combobox(manage_frame, state="readonly", font=("Arial", 12), width=35)
        self.user_combobox.grid(row=0, column=1, padx=10)
        
        tk.Button(manage_frame, text="❌ ลบข้อมูล (Delete)", command=self.delete_selected_user, bg="#f44336", fg="white", font=("Arial", 12)).grid(row=0, column=2, padx=10)

    def refresh_user_list(self):
        """Fetch users from database and update combobox"""
        users = get_all_users()
        # Format display string as 'Name (ID)'
        self.user_display_map = {f"{u['user_name']} ({u['id']})": u['id'] for u in users}
        
        self.user_combobox['values'] = list(self.user_display_map.keys())
        if self.user_combobox['values']:
            self.user_combobox.current(0)
        else:
            self.user_combobox.set('')

    def delete_selected_user(self):
        selected_text = self.user_combobox.get()
        if not selected_text:
            messagebox.showwarning("Warning", "กรุณาเลือกผู้ใช้งานที่ต้องการลบ\n(Please select a user to delete)")
            return
            
        user_id = self.user_display_map.get(selected_text)
        
        confirm = messagebox.askyesno("Confirm Delete", f"คุณแน่ใจหรือไม่ว่าต้องการลบผู้ใช้:\n{selected_text}\n(Are you sure you want to delete this user?)")
        if confirm:
            if delete_user(user_id):
                messagebox.showinfo("Success", "ลบผู้ใช้เรียบร้อยแล้ว!\n(User deleted successfully)")
                self.refresh_user_list()
            else:
                messagebox.showerror("Error", "เกิดข้อผิดพลาด ไม่สามารถลบผู้ใช้งานได้\n(Failed to delete user)")

    def display_image(self, cv2_img, angle):
        # Convert to RGB for PIL
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        # Resize to fit label
        pil_img = pil_img.resize((180, 180), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(pil_img)
        
        self.img_labels[angle].config(image=tk_img, text="")
        self.img_labels[angle].image = tk_img # Keep reference
        
        self.captured_images[angle] = cv2_img

    def capture_from_webcam(self, angle):
        messagebox.showinfo("Webcam", f"ถ่ายรูปด้าน: {angle.capitalize()}\nกด Spacebar เพื่อถ่ายรูป \nกด ESC เพื่อยกเลิก")
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret:
                messagebox.showerror("Error", "ไม่สามารถเปิดกล้องได้")
                break
            cv2.imshow(f"Capture {angle.capitalize()} (Space to snap, ESC to cancel)", frame)
            
            key = cv2.waitKey(1)
            if key == 32: # Space
                self.display_image(frame.copy(), angle)
                break
            elif key == 27: # ESC
                break
                
        cap.release()
        cv2.destroyAllWindows()

    def choose_from_file(self, angle):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None:
                self.display_image(img, angle)
            else:
                messagebox.showerror("Error", "ไม่สามารถอ่านไฟล์รูปภาพได้")

    def register_user(self):
        user_id = self.entries["รหัสนักศึกษา/พนักงาน (ID):"].get().strip()
        name = self.entries["ชื่อผู้ใช้งาน (Name):"].get().strip()
        gender = self.entries["เพศ (Gender):"].get().strip()
        faculty = self.entries["คณะ (Faculty):"].get().strip()
        dept = self.entries["สาขา (Department):"].get().strip()

        if not all([user_id, name, gender, faculty, dept]):
            messagebox.showwarning("Incomplete", "กรุณากรอกข้อมูลให้ครบถ้วน!\n(Please fill all fields)")
            return

        if self.captured_images["front"] is None:
            messagebox.showwarning("No Image", "กรุณาเพิ่มรูปใบหน้าด้านหน้าเป็นอย่างน้อย!\n(Please provide at least a Front face image)")
            return

        # 1. Extract Embedding
        messagebox.showinfo("Processing", "กำลังสกัดใบหน้า... (Extracting face features)")
        try:
            embeddings_dict = {}
            for angle, img in self.captured_images.items():
                if img is None:
                    continue
                    
                # Resize image if it's too huge to prevent MTCNN from taking too much memory/time
                img_to_process = img
                max_size = 1000
                height, width = img_to_process.shape[:2]
                if max(height, width) > max_size:
                    scale = max_size / max(height, width)
                    img_to_process = cv2.resize(img_to_process, (int(width * scale), int(height * scale)))

                results = DeepFace.represent(img_to_process, model_name="Facenet512", enforce_detection=False, detector_backend="mtcnn")
                if results:
                    embeddings_dict[angle] = results[0]["embedding"]
                else:
                    messagebox.showwarning("Warning", f"ไม่พบใบหน้าในรูปด้าน {angle}!")
                    
            if not embeddings_dict:
                 messagebox.showerror("Error", "สกัดใบหน้าล้มเหลว ไม่พบใบหน้าเลยสักรูปเดียว!")
                 return
            
            # 2. Save to Database
            success = add_user(user_id, name, gender, faculty, dept, embeddings_dict)
            
            if success:
                messagebox.showinfo("Success", f"ลงทะเบียนคุณ {name} เรียบร้อยแล้ว!\n(Registration successful)")
                self.reset_form()
                self.refresh_user_list() # Update delete list
            else:
                messagebox.showerror("Database Error", "ไม่สามารถบันทึกข้อมูลได้")
                
        except Exception as e:
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการประมวลผล:\n{str(e)}")

    def reset_form(self):
        for entry in self.entries.values():
            if isinstance(entry, tk.Entry):
                entry.delete(0, tk.END)
            elif isinstance(entry, ttk.Combobox):
                entry.set('')
        
        self.captured_images = {"front": None, "left": None, "right": None}
        for angle, lbl in self.img_labels.items():
            lbl.config(image='', text=f"No {angle} image")

if __name__ == "__main__":
    root = tk.Tk()
    app = RegistrationApp(root)
    root.mainloop()
