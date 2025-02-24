from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(255), index=True, nullable=False)
    essay = Column(Text, nullable=False)
    questions = Column(Text, nullable=False)
    image_url = Column(String(1024))  # Add column for storing image URL
    created_at = Column(DateTime, default=datetime.utcnow)

# Create database engine and session
engine = create_engine("sqlite:///./exercises.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 