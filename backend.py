import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "taalika.db"
KNOWLEDGE_BASE = [
    {"topic": "admissions", "text": "New students can join a free 30-minute orientation class before enrolling. Admissions are open year-round when a batch has space. Students should bring comfortable clothing, a water bottle, and a notebook. No prior experience is needed for Bharatanatyam Foundations or Bollywood Performance Lab."},
    {"topic": "fees", "text": "Bharatanatyam Foundations costs Rs. 8,500 for 12 weeks. Bharatanatyam Repertoire costs Rs. 12,000 for 16 weeks. Kathak Rhythm and Spin costs Rs. 9,500 for 12 weeks. Bollywood Performance Lab costs Rs. 6,500 for 8 weeks. Fees can be paid online or at the front desk. A 10 percent sibling discount is available."},
    {"topic": "schedule", "text": "Bharatanatyam Foundations runs Tuesday and Thursday from 6:30 to 7:45 PM in Studio A. Bharatanatyam Repertoire runs Monday and Wednesday from 7:00 to 8:30 PM in Studio A. Kathak runs Saturday from 10:00 to 11:30 AM in Studio B. Bollywood runs Friday from 6:30 to 8:00 PM in Studio B."},
    {"topic": "instructors", "text": "Ananya Rao is the Artistic Director and teaches Bharatanatyam. Meera Iyer is Senior Faculty for Bharatanatyam foundations. Kabir Khan is Guest Faculty for Kathak and specializes in rhythm and footwork. The academy keeps batches small so instructors can give individual feedback."},
    {"topic": "policies", "text": "Students may make up one missed class per month in another batch with advance notice and faculty approval. Fees are non-refundable after the second class, but a batch transfer may be requested within the first two weeks. Students should arrive 10 minutes early, keep phones silent, and avoid wearing heavy jewelry during practice."},
    {"topic": "events", "text": "Taalika hosts an Open Studio Evening on October 12 at 6:00 PM, a Deepavali Showcase on November 2 at 7:30 PM, and a Rhythm Workshop with Kabir Khan on November 16 at 11:00 AM. Event seats can be reserved through the Events page."},
    {"topic": "academy", "text": "Taalika Dance Academy is a warm, rigorous studio for Indian classical and contemporary movement. The academy is located at 24 Lotus Lane, Indiranagar, Bengaluru. It is open Monday to Saturday from 9:30 AM to 8:30 PM. Contact the front desk at +91 80 4123 7788."},
]

DANCER_KEYWORDS = {
    "academy", "admission", "beginner", "bharatanatyam", "bollywood", "class",
    "course", "dance", "dancer", "fees", "instructor", "kathak", "lesson",
    "practice", "schedule", "studio", "training", "workshop", "orientation",
    "location", "address", "where", "directions",
}
NON_DANCER_KEYWORDS = {
    "singer", "singing", "song", "vocal", "vocals", "music", "actor", "acting",
    "theatre", "theater", "instrument", "guitar", "piano",
}

app = FastAPI(title="Taalika Dance Academy API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AdmissionRequest(BaseModel):
    participant_type: Literal["dancer"]
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=120)
    course: str = Field(min_length=2, max_length=120)
    experience: str = Field(min_length=2, max_length=80)
    goals: str = Field(default="", max_length=2000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                course TEXT NOT NULL,
                experience TEXT NOT NULL,
                goals TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(admissions)").fetchall()}
        if "location" not in columns:
            connection.execute("ALTER TABLE admissions ADD COLUMN location TEXT NOT NULL DEFAULT ''")


def tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_context(question: str, limit: int = 2):
    query_tokens = set(tokenize(question))
    scored = []
    for item in KNOWLEDGE_BASE:
        counts = Counter(tokenize(item["text"]))
        overlap = sum(counts[word] for word in query_tokens)
        topic_bonus = 2 if item["topic"] in query_tokens else 0
        scored.append((overlap + topic_bonus, item))
    scored.sort(key=lambda entry: entry[0], reverse=True)
    return [item for score, item in scored[:limit] if score > 0]


def answer_question(question: str):
    if not set(tokenize(question)).intersection(DANCER_KEYWORDS):
        return (
            "I am here for dancers and people exploring dance training at Taalika. "
            "Ask me about classes, schedules, fees, instructors, admissions, events, or the studio location.",
            [],
        )
    matches = retrieve_context(question)
    if not matches:
        return (
            "I could not find that in the academy guide yet. Please contact "
            "the front desk at +91 80 4123 7788 and our team will help you.",
            [],
        )
    answer = matches[0]["text"]
    if len(matches) > 1:
        answer += "\n\nRelated note: " + matches[1]["text"]
    return answer, [item["topic"] for item in matches]


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/health")
def health():
    return {"status": "ok", "service": "taalika-api"}


@app.post("/admissions", status_code=201)
def create_admission(request: AdmissionRequest):
    request_text = " ".join((request.course, request.experience, request.goals)).lower()
    if set(tokenize(request_text)).intersection(NON_DANCER_KEYWORDS):
        raise HTTPException(
            status_code=400,
            detail="Taalika admissions are only for dance training. Please choose a dance course and describe your dance goals.",
        )
    created_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO admissions (name, email, phone, location, course, experience, goals, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (request.name, "", request.phone, request.location, request.course, request.experience, request.goals, created_at),
        )
        return {"id": cursor.lastrowid, "message": "Orientation request received", "created_at": created_at}


@app.get("/admissions")
def list_admissions(limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, phone, location, course, experience, goals, created_at FROM admissions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer, sources = answer_question(request.question)
    return {"answer": answer, "sources": sources}
