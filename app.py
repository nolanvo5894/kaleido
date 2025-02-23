from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import asyncio
import os
from typing import Dict, Optional, List
from workflow import generate_exercise, read_markdown_file
from models import Exercise, get_db
import openai
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from elevenlabs.client import ElevenLabs
from elevenlabs import save

app = FastAPI(title="IELTS Exercise Generator API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TopicRequest(BaseModel):
    topic: str

class ExerciseResponse(BaseModel):
    essay: Optional[str] = None
    questions: Optional[str] = None
    status: str
    error: Optional[str] = None

class ExerciseDB(BaseModel):
    id: int
    topic: str
    created_at: datetime
    class Config:
        orm_mode = True

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": str(exc)}
    )

@app.post("/api/generate", response_model=ExerciseResponse)
async def generate_ielts_exercise(request: TopicRequest, db: Session = Depends(get_db)):
    try:
        # Validate input
        if not request.topic or len(request.topic.strip()) == 0:
            raise HTTPException(status_code=400, detail="Topic cannot be empty")

        # Check if we already have this topic
        existing_exercise = db.query(Exercise).filter(
            Exercise.topic.ilike(request.topic.strip())
        ).first()
        
        if existing_exercise:
            return ExerciseResponse(
                essay=existing_exercise.essay,
                questions=existing_exercise.questions,
                status="success"
            )

        # Create publication directory if it doesn't exist
        os.makedirs('publication', exist_ok=True)
        
        # Generate the exercise
        result = await generate_exercise(request.topic)
        
        # Read the generated files
        essay = read_markdown_file('publication/final_essay.md')
        questions = read_markdown_file('publication/questions.md')
        
        if not essay or not questions:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate exercise content"
            )
        
        # Store in database
        try:
            db_exercise = Exercise(
                topic=request.topic,
                essay=essay,
                questions=questions
            )
            db.add(db_exercise)
            db.commit()
            db.refresh(db_exercise)
        except Exception as e:
            print(f"Database error: {str(e)}")
            # Continue even if database storage fails
        
        return ExerciseResponse(
            essay=essay,
            questions=questions,
            status="success"
        )
    except Exception as e:
        print(f"Error generating exercise: {str(e)}")  # For debugging
        return ExerciseResponse(
            status="error",
            error=str(e)
        )

@app.post("/api/generate-audio")
async def generate_audio(request: TopicRequest):
    try:
        # Get the essay content
        essay_path = 'publication/final_essay.md'
        if not os.path.exists(essay_path):
            raise HTTPException(status_code=404, detail="Essay not found")
            
        with open(essay_path, 'r', encoding='utf-8') as f:
            essay_content = f.read()
        
        # Create audio directory if it doesn't exist
        audio_dir = Path('publication/audio')
        audio_dir.mkdir(exist_ok=True)
        
        # Generate speech using ElevenLabs
        client = ElevenLabs()
        
        audio = client.text_to_speech.convert(
            text=essay_content,
            voice_id="JBFqnCBsd6RMkjVDRZzb",  # You can change this to your preferred voice
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        # Save the audio file
        speech_file_path = audio_dir / "essay_reading.mp3"
        save(audio, str(speech_file_path))
        
        return {"status": "success", "message": "Audio generated successfully"}
        
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    audio_path = f"publication/audio/{filename}"
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path)

@app.get("/api/exercises", response_model=List[ExerciseDB])
async def get_exercises(db: Session = Depends(get_db)):
    exercises = db.query(Exercise).order_by(Exercise.created_at.desc()).all()
    return exercises

@app.get("/api/exercises/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ExerciseResponse(
        essay=exercise.essay,
        questions=exercise.questions,
        status="success"
    )

# Mount the static frontend files
app.mount("/", StaticFiles(directory="static", html=True), name="static")