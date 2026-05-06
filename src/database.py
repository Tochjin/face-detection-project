from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
import numpy as np

# Change this if your PostgreSQL password is different
DATABASE_URL = "postgresql://postgres:todeiei7101@localhost:5432/face_detection"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, index=True) # User ID provided by admin
    user_name = Column(String, nullable=False)
    gender = Column(String)
    faculty = Column(String)
    department = Column(String)
    
    # One to Many relationship for face embeddings
    face_embeddings = relationship("FaceEmbedding", back_populates="user", cascade="all, delete-orphan")

class FaceEmbedding(Base):
    __tablename__ = 'face_embeddings'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    angle = Column(String) # e.g. "front", "left", "right"
    embedding = Column(Vector(512)) # Facenet512 outputs a 512-dimension vector
    
    user = relationship("User", back_populates="face_embeddings")

class AccessLog(Base):
    __tablename__ = 'access_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    access_time = Column(DateTime, default=datetime.utcnow)

def setup_database():
    """Create the tables in PostgreSQL"""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified successfully.")

def add_user(user_id, user_name, gender, faculty, department, embeddings_dict):
    """
    Add a new user and map multiple face embeddings (e.g. front, left, right) 
    to the database. 
    embeddings_dict format: {"front": [vector], "left": [vector], ...}
    """
    db = SessionLocal()
    try:
        # Merge the basic user info
        user = User(
            id=user_id,
            user_name=user_name,
            gender=gender,
            faculty=faculty,
            department=department
        )
        db.merge(user)
        db.commit() # Commit to ensure user_id is in the database
        
        # Now add/update embeddings for this user
        # 1. We could delete old ones, or just let 'merge' handle it if we had fixed IDs,
        # but the simplest way is to clear old ones to prevent accumulation if they re-register.
        db.query(FaceEmbedding).filter(FaceEmbedding.user_id == user_id).delete()
        
        # 2. Add the new ones
        for angle, embedding_list in embeddings_dict.items():
            if embedding_list is not None:
                new_face = FaceEmbedding(
                    user_id=user_id,
                    angle=angle,
                    embedding=embedding_list
                )
                db.add(new_face)
                
        db.commit()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

from scipy.spatial.distance import cosine

def find_closest_user(query_embedding, threshold=0.35):
    """Find the user in the database with the closest face embedding using Cosine Distance"""
    db = SessionLocal()
    try:
        vector_element = np.array(query_embedding)
        
        # Search against all face embeddings in the DB
        closest_face = db.query(FaceEmbedding).order_by(FaceEmbedding.embedding.cosine_distance(vector_element)).first()
        
        if not closest_face:
            return None
            
        # Re-verify distance in Python using scipy's cosine
        distance = cosine(closest_face.embedding, vector_element)
        
        if distance < threshold:
            # We get the user metadata using the SQLAlchemy relationship `closest_face.user`
            user = closest_face.user
            return {
                "id": user.id,
                "user_name": user.user_name,
                "gender": user.gender,
                "faculty": user.faculty,
                "department": user.department,
                "distance": distance,
                "matched_angle": closest_face.angle
            }
        return None
    finally:
        db.close()

def get_all_users():
    """Retrieve a list of all currently registered users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [{"id": u.id, "user_name": u.user_name} for u in users]
    finally:
        db.close()

def delete_user(user_id):
    """Delete a user from the database by ID"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def log_user_access(user_id):
    """Log access into PostgreSQL"""
    db = SessionLocal()
    try:
        new_log = AccessLog(user_id=user_id, access_time=datetime.now())
        db.add(new_log)
        db.commit()
        print(f"บันทึกการเข้าใช้งานของรหัส {user_id} เรียบร้อยแล้ว (PostgreSQL)")
    except Exception as e:
        print(f"Error logging access: {e}")
        db.rollback()
    finally:
        db.close()
