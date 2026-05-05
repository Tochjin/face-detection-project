import sys
from pathlib import Path

# Add src to python path so we can import modules
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from src.database import setup_database, add_user

def main():
    print("=== ระบบลงทะเบียนผู้ใช้งาน (User Registration System) ===")
    
    # Ensure database is set up
    setup_database()
    
    user_name = input("ชื่อผู้ใช้งาน (Name - ต้องตรงกับชื่อไฟล์รูปภาพ): ").strip()
    if not user_name:
        print("ข้อผิดพลาด: ชื่อผู้ใช้งานไม่สามารถเว้นว่างได้ (Error: Name cannot be empty)")
        return

    gender = input("เพศ (Gender): ").strip()
    faculty = input("คณะ (Faculty): ").strip()
    department = input("สาขา/แผนก (Department): ").strip()

    print("\nกำลังบันทึกข้อมูล...")
    success = add_user(user_name, gender, faculty, department)
    
    if success:
        print(f"\nลงทะเบียนผู้ใช้ '{user_name}' สำเร็จ! (Successfully registered)")
        print(f"อย่าลืมนำรูปภาพไปไว้ที่โฟลเดอร์: {BASE_DIR / 'data' / 'face_db'} โดยตั้งชื่อไฟล์เป็น {user_name}.jpg")
    else:
        print("\nเกิดข้อผิดพลาดในการลงทะเบียน (Failed to register user)")

if __name__ == "__main__":
    main()
