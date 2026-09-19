import re
import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen
from collections import Counter

import streamlit as st


st.set_page_config(
    page_title="Taalika Dance Academy",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("TAALIKA_API_URL", "http://127.0.0.1:8000").rstrip("/")
STUDIO_ADDRESS = "24 Lotus Lane, Indiranagar, Bengaluru"
MAP_URL = "https://www.google.com/maps/search/?api=1&query=24+Lotus+Lane+Indiranagar+Bengaluru"
NON_DANCER_TERMS = {"singer", "singing", "song", "vocal", "vocals", "music", "actor", "acting", "theatre", "theater", "instrument", "guitar", "piano"}

# -----------------------------
# Academy data and local RAG corpus
# -----------------------------
COURSES = [
    {
        "name": "Bharatanatyam Foundations",
        "level": "Beginner",
        "duration": "12 weeks",
        "fee": "Rs. 8,500",
        "days": "Tue & Thu",
        "time": "6:30 - 7:45 PM",
        "color": "saffron",
        "image": "https://commons.wikimedia.org/wiki/Special:FilePath/Barathanatyam_dancer.jpg?width=1200",
        "image_alt": "Bharatanatyam dancer in traditional Indian costume performing a classical pose",
        "description": "Build strong adavus, posture, hand gestures, rhythm, and expressive storytelling from the ground up.",
        "tags": "adavus, mudras, abhinaya, beginner",
    },
    {
        "name": "Bharatanatyam Repertoire",
        "level": "Intermediate",
        "duration": "16 weeks",
        "fee": "Rs. 12,000",
        "days": "Mon & Wed",
        "time": "7:00 - 8:30 PM",
        "color": "indigo",
        "image": "https://images.unsplash.com/photo-1504609813442-a8924e83f76e?auto=format&fit=crop&w=900&q=85",
        "image_alt": "Indian classical dancer in traditional costume performing on stage",
        "description": "Deepen technique and learn a complete margam with jathis, varnams, padams, and stagecraft.",
        "tags": "margam, varnam, stagecraft, intermediate",
    },
    {
        "name": "Kathak: Rhythm & Spin",
        "level": "Open level",
        "duration": "12 weeks",
        "fee": "Rs. 9,500",
        "days": "Sat",
        "time": "10:00 - 11:30 AM",
        "color": "teal",
            "image": "https://commons.wikimedia.org/wiki/Special:FilePath/Kathak_Dance_at_Kamani_Auditorium_01.jpg?width=1200",
        "image_alt": "Kathak dancer moving with rhythm and expressive hand gestures",
        "description": "Explore tatkar, chakkars, tukras, and graceful storytelling through Hindustani rhythm.",
        "tags": "tatkar, chakkars, tukras, kathak",
    },
    {
        "name": "Bollywood Performance Lab",
        "level": "Open level",
        "duration": "8 weeks",
        "fee": "Rs. 6,500",
        "days": "Fri",
        "time": "6:30 - 8:00 PM",
        "color": "coral",
        "image": "https://images.unsplash.com/photo-1535525153412-5a42439a210d?auto=format&fit=crop&w=900&q=85",
        "image_alt": "Bollywood dancer performing in contemporary western dancewear",
        "description": "Train musicality, commercial choreography, performance energy, and camera confidence.",
        "tags": "bollywood, choreography, performance",
    },
]

INSTRUCTORS = [
    {"name": "Ananya Rao", "role": "Artistic Director", "style": "Bharatanatyam", "years": "18 years", "initials": "AR", "image": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=700&q=85", "bio": "A performer and teacher committed to making classical technique feel alive, rigorous, and personal."},
    {"name": "Meera Iyer", "role": "Senior Faculty", "style": "Bharatanatyam", "years": "12 years", "initials": "MI", "image": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=700&q=85", "bio": "Known for patient foundations classes and an approach that connects rhythm with everyday movement."},
    {"name": "Kabir Khan", "role": "Guest Faculty", "style": "Kathak", "years": "10 years", "initials": "KK", "image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=700&q=85", "bio": "A rhythm specialist who brings clarity, warmth, and a little theatrical sparkle to every class."},
]

SCHEDULE = [
    ("Monday", "Bharatanatyam Repertoire", "7:00 - 8:30 PM", "Studio A", "Intermediate"),
    ("Tuesday", "Bharatanatyam Foundations", "6:30 - 7:45 PM", "Studio A", "Beginner"),
    ("Wednesday", "Bharatanatyam Repertoire", "7:00 - 8:30 PM", "Studio A", "Intermediate"),
    ("Thursday", "Bharatanatyam Foundations", "6:30 - 7:45 PM", "Studio A", "Beginner"),
    ("Friday", "Bollywood Performance Lab", "6:30 - 8:00 PM", "Studio B", "Open level"),
    ("Saturday", "Kathak: Rhythm & Spin", "10:00 - 11:30 AM", "Studio B", "Open level"),
]

EVENTS = [
    ("OCT", "12", "Open Studio Evening", "Watch a live class, meet the faculty, and try a 20-minute movement sequence.", "6:00 PM", "Free", "https://images.unsplash.com/photo-1508807526345-15e9b5f4eaff?auto=format&fit=crop&w=900&q=85"),
    ("NOV", "02", "Deepavali Showcase", "An intimate evening of classical and contemporary works by the Taalika community.", "7:30 PM", "Rs. 500", "https://images.unsplash.com/photo-1531058020387-3be344556be6?auto=format&fit=crop&w=900&q=85"),
    ("NOV", "16", "Rhythm Workshop", "A Saturday workshop on tala, footwork, and improvisation with Kabir Khan.", "11:00 AM", "Rs. 800", "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=900&q=85"),
]

KNOWLEDGE_BASE = [
    {"topic": "admissions", "text": "New students can join a free 30-minute orientation class before enrolling. Admissions are open year-round when a batch has space. Students should bring comfortable clothing, a water bottle, and a notebook. No prior experience is needed for Bharatanatyam Foundations or Bollywood Performance Lab."},
    {"topic": "fees", "text": "Bharatanatyam Foundations costs Rs. 8,500 for 12 weeks. Bharatanatyam Repertoire costs Rs. 12,000 for 16 weeks. Kathak Rhythm and Spin costs Rs. 9,500 for 12 weeks. Bollywood Performance Lab costs Rs. 6,500 for 8 weeks. Fees can be paid online or at the front desk. A 10 percent sibling discount is available."},
    {"topic": "schedule", "text": "Bharatanatyam Foundations runs Tuesday and Thursday from 6:30 to 7:45 PM in Studio A. Bharatanatyam Repertoire runs Monday and Wednesday from 7:00 to 8:30 PM in Studio A. Kathak runs Saturday from 10:00 to 11:30 AM in Studio B. Bollywood runs Friday from 6:30 to 8:00 PM in Studio B."},
    {"topic": "instructors", "text": "Ananya Rao is the Artistic Director and teaches Bharatanatyam. Meera Iyer is Senior Faculty for Bharatanatyam foundations. Kabir Khan is Guest Faculty for Kathak and specializes in rhythm and footwork. The academy keeps batches small so instructors can give individual feedback."},
    {"topic": "policies", "text": "Students may make up one missed class per month in another batch with advance notice and faculty approval. Fees are non-refundable after the second class, but a batch transfer may be requested within the first two weeks. Students should arrive 10 minutes early, keep phones silent, and avoid wearing heavy jewelry during practice."},
    {"topic": "events", "text": "Taalika hosts an Open Studio Evening on October 12 at 6:00 PM, a Deepavali Showcase on November 2 at 7:30 PM, and a Rhythm Workshop with Kabir Khan on November 16 at 11:00 AM. Event seats can be reserved through the Events page."},
    {"topic": "academy", "text": "Taalika Dance Academy is a warm, rigorous studio for Indian classical and contemporary movement. The academy is located at 24 Lotus Lane, Indiranagar, Bengaluru. It is open Monday to Saturday from 9:30 AM to 8:30 PM. Contact hello@taalika.example or +91 80 4123 7788."},
]


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_context(question, limit=2):
    query_tokens = set(tokenize(question))
    scored = []
    for item in KNOWLEDGE_BASE:
        words = tokenize(item["text"])
        counts = Counter(words)
        overlap = sum(counts[word] for word in query_tokens)
        topic_bonus = 2 if item["topic"] in query_tokens else 0
        scored.append((overlap + topic_bonus, item))
    scored.sort(key=lambda entry: entry[0], reverse=True)
    return [item for score, item in scored[:limit] if score > 0]


def answer_question(question):
    matches = retrieve_context(question)
    if not matches:
        return "I could not find that in the academy guide yet. Please contact the front desk at +91 80 4123 7788 and our team will help you."
    best = matches[0]
    response = best["text"]
    if len(matches) > 1:
        response += "\n\nRelated note: " + matches[1]["text"]
    return response


def api_request(method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(f"{API_URL}{path}", data=body, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


# -----------------------------
# Styling and small view helpers
# -----------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
:root { --ink: #24221f; --muted: #746e66; --cream: #f6f1e9; --paper: #fffdf9; --saffron: #d97745; --teal: #1f7775; --line: #e7ddd0; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
.stApp { background: var(--cream); }
[data-testid="stSidebar"] { background: #202b2a; border-right: 0; }
[data-testid="stSidebar"] * { color: #f8f2e9 !important; }
[data-testid="stSidebar"] .stRadio label { padding: 8px 10px; border-radius: 4px; }
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,.08); }
h1, h2, h3 { font-family: 'Playfair Display', serif; letter-spacing: 0; }
h1 { font-size: clamp(2.7rem, 6vw, 5.6rem); line-height: .98; margin: 0; }
h2 { font-size: clamp(1.9rem, 3vw, 3rem); }
h3 { font-size: 1.35rem; }
p { line-height: 1.65; }
.hero { padding: 4.5rem 0 3rem; min-height: 420px; background: linear-gradient(120deg, rgba(32,43,42,.92) 0%, rgba(32,43,42,.62) 55%, rgba(32,43,42,.18) 100%), url('https://commons.wikimedia.org/wiki/Special:FilePath/Kathak_Group_Performance_(1).jpg?width=1800') center/cover; border-radius: 4px; color: white; padding-left: 4rem; display: flex; align-items: center; }
.hero p { max-width: 580px; color: #eee2d4; font-size: 1.05rem; }
.eyebrow { color: var(--saffron); font-weight: 700; font-size: .74rem; text-transform: uppercase; letter-spacing: .16em; margin-bottom: 1rem; }
.stat { background: var(--paper); border-top: 3px solid var(--saffron); padding: 1.2rem; min-height: 122px; }
.stat strong { display: block; color: var(--teal); font: 700 2rem 'Playfair Display', serif; }
.stat span { color: var(--muted); font-size: .9rem; }
.section { padding: 2.5rem 0 1rem; }
.panel { background: var(--paper); border: 1px solid var(--line); padding: 1.35rem; border-radius: 3px; height: 100%; }
.course-card { background: var(--paper); border: 1px solid var(--line); border-left: 5px solid var(--saffron); padding: 1.4rem; min-height: 260px; }
.course-image { width: 100%; height: 150px; object-fit: cover; display: block; margin: -1.4rem -1.4rem 1.2rem; width: calc(100% + 2.8rem); filter: saturate(.85); }
.home-dance-image { width: 100%; height: 360px; object-fit: cover; display: block; border-radius: 3px; filter: saturate(.9); }
.course-card.indigo { border-left-color: #5d698f; } .course-card.teal { border-left-color: var(--teal); } .course-card.coral { border-left-color: #c96062; }
.course-card h3 { margin-top: 0; }
.meta { color: var(--muted); font-size: .88rem; }
.price { color: var(--teal); font-size: 1.35rem; font-weight: 700; }
.badge { display: inline-block; background: #ece2d4; color: #735239; padding: 4px 8px; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; margin-bottom: .8rem; }
.quote { border-left: 3px solid var(--saffron); padding: .2rem 0 .2rem 1.3rem; color: var(--muted); font-style: italic; }
.event-date { background: #202b2a; color: white; text-align: center; padding: .8rem .5rem; }
.event-date strong { display: block; font: 700 1.8rem 'Playfair Display', serif; color: #f3c58d; }
.footer { margin-top: 3rem; padding: 2rem 0; border-top: 1px solid var(--line); color: var(--muted); font-size: .9rem; }
div.stButton > button { border-radius: 2px; border: 1px solid var(--teal); color: var(--teal); background: transparent; font-weight: 700; }
div.stButton > button:hover { color: white; background: var(--teal); border-color: var(--teal); }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div { border-radius: 2px; border-color: var(--line); background: var(--paper); }
@media (max-width: 700px) { .hero { padding: 2.5rem 1.4rem; min-height: 460px; } h1 { font-size: 3.2rem; } }
</style>
""",
    unsafe_allow_html=True,
)


def brand_mark():
    st.sidebar.markdown("<div style='font:700 1.7rem Playfair Display,serif; margin: .4rem 0 0'>taalika</div><div style='font-size:.7rem;letter-spacing:.2em;color:#f3c58d'>DANCE ACADEMY</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,.15);margin:1.5rem 0'>", unsafe_allow_html=True)


def page_header(kicker, title, description):
    st.markdown(f"<div class='eyebrow'>{kicker}</div><h1 style='font-size:3.6rem;margin-bottom:.7rem'>{title}</h1><p style='max-width:680px;color:#746e66'>{description}</p>", unsafe_allow_html=True)


def course_card(course):
    st.markdown(f"<div class='course-card {course['color']}'> <img class='course-image' src='{course['image']}' alt='{course['image_alt']}'><span class='badge'>{course['level']}</span><h3>{course['name']}</h3><p>{course['description']}</p><div class='meta'>{course['days']} &nbsp;|&nbsp; {course['time']} &nbsp;|&nbsp; {course['duration']}</div><div style='margin-top:1rem' class='price'>{course['fee']}</div></div>", unsafe_allow_html=True)


# -----------------------------
# Pages
# -----------------------------
brand_mark()
dancer_access = st.sidebar.checkbox("I am a dancer or exploring dance training")
if not dancer_access:
    st.markdown("<div class='hero'><div><div class='eyebrow' style='color:#f3c58d'>Dancer access</div><h1>Practice starts here.</h1><p>Taalika is a dancer-only academy website for students, performers, and people beginning dance training. Confirm your dancer access in the sidebar to continue.</p></div></div>", unsafe_allow_html=True)
    st.stop()

page = st.sidebar.radio("Explore", ["Home", "Courses", "Schedule", "Instructors", "Fees", "Events", "Admissions", "Visit Us", "Ask Taalika"], label_visibility="collapsed")
st.sidebar.markdown("<div style='position:fixed;bottom:1.5rem;font-size:.78rem;color:#b9c1b7'>A studio for rhythm, story, and presence.<br>Indiranagar, Bengaluru</div>", unsafe_allow_html=True)

if page == "Home":
    st.markdown("<section class='hero'><div><div class='eyebrow' style='color:#f3c58d'>Move with meaning</div><h1>Find your<br>natural rhythm.</h1><p>Classical discipline, contemporary energy, and a studio community that gives every student room to grow.</p></div></section>", unsafe_allow_html=True)
    st.markdown("<div class='section'><div class='eyebrow'>Dance in motion</div><h2>Every style has a story.</h2><div class='panel'><img class='home-dance-image' src='https://commons.wikimedia.org/wiki/Special:FilePath/Kathak_Dance_at_Kamani_Auditorium_01.jpg?width=1500' alt='Indian classical dancers performing on an auditorium stage'><p style='margin-bottom:0'>From the geometry of Bharatanatyam to the sweep of Kathak and the pulse of Bollywood, our studio makes space for many ways of moving.</p></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='section'><div class='eyebrow'>The Taalika way</div><h2>A little more than a class.</h2></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for col, (value, label) in zip(cols, [("4", "signature programs"), ("18", "years of teaching"), ("1:12", "mentor ratio"), ("6", "days a week")]):
        with col:
            st.markdown(f"<div class='stat'><strong>{value}</strong><span>{label}</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='section'><div class='eyebrow'>Start here</div><h2>Choose your next step.</h2></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown("<div class='panel'><h3>Learn the foundations</h3><p>Start with posture, rhythm, and expressive movement in a supportive beginner batch.</p></div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown("<div class='panel'><h3>Find your class</h3><p>Browse our weekly schedule, compare course fees, and reserve an orientation class.</p></div>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown("<div class='panel'><h3>Ask the studio</h3><p>Get a quick answer from our academy guide about timings, policies, and enrollment.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='section'><div class='quote'>Dance is not only what the body remembers. It is what the room makes possible.</div></div>", unsafe_allow_html=True)

elif page == "Courses":
    page_header("Programs", "Courses with a point of view.", "Whether you are taking your first step or returning to a practice you love, each course is built around clear progress and generous feedback.")
    filter_level = st.selectbox("Filter by level", ["All levels", "Beginner", "Intermediate", "Open level"])
    shown = [course for course in COURSES if filter_level == "All levels" or course["level"] == filter_level]
    cols = st.columns(2)
    for index, course in enumerate(shown):
        with cols[index % 2]:
            course_card(course)
            st.write("")
    st.markdown("<div class='panel'><h3>Not sure where you fit?</h3><p>Book the free orientation class. We will listen to your experience, understand your goals, and recommend a batch that feels challenging but kind.</p></div>", unsafe_allow_html=True)

elif page == "Schedule":
    page_header("Weekly rhythm", "Your week, in counts.", "Our timetable is deliberately small: fewer batches, better attention, and enough breathing room to build a real practice.")
    for day, course, timing, studio, level in SCHEDULE:
        left, middle, right = st.columns([1.3, 3.5, 2.2])
        with left:
            st.markdown(f"<div style='font:700 1.2rem Playfair Display,serif;padding:1.1rem 0;border-bottom:1px solid #e7ddd0'>{day}</div>", unsafe_allow_html=True)
        with middle:
            st.markdown(f"<div style='padding:1.1rem 0;border-bottom:1px solid #e7ddd0'><strong>{course}</strong><br><span class='meta'>{level}</span></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div style='padding:1.1rem 0;border-bottom:1px solid #e7ddd0;color:#746e66'>{timing}<br>{studio}</div>", unsafe_allow_html=True)
    st.info("The studio is closed on Sundays. Missed-class makeups are available with advance notice and faculty approval.")

elif page == "Instructors":
    page_header("The people in the room", "Meet your guides.", "Our faculty teach technique without losing the joy that brought us to dance in the first place.")
    cols = st.columns(3)
    for col, teacher in zip(cols, INSTRUCTORS):
        with col:
            st.markdown(f"<div class='panel'><img src='{teacher['image']}' alt='{teacher['name']}' style='width:100%;height:220px;object-fit:cover;display:block;filter:saturate(.8)'><div style='padding-top:1rem'><span class='badge'>{teacher['style']}</span><h3>{teacher['name']}</h3><div class='meta'>{teacher['role']} &nbsp;|&nbsp; {teacher['years']}</div><p>{teacher['bio']}</p></div></div>", unsafe_allow_html=True)

elif page == "Fees":
    page_header("Simple, transparent", "Invest in your practice.", "All course fees include weekly instruction, access to practice notes, and one community studio session each term.")
    for course in COURSES:
        left, middle, right = st.columns([3, 2, 1.5])
        with left:
            st.markdown(f"<div style='padding:1rem 0;border-bottom:1px solid #e7ddd0'><strong>{course['name']}</strong><br><span class='meta'>{course['duration']} &nbsp;|&nbsp; {course['level']}</span></div>", unsafe_allow_html=True)
        with middle:
            st.markdown(f"<div style='padding:1rem 0;border-bottom:1px solid #e7ddd0;color:#746e66'>{course['days']}<br>{course['time']}</div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<div style='padding:1rem 0;border-bottom:1px solid #e7ddd0;text-align:right'><span class='price'>{course['fee']}</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='section'><div class='panel'><h3>Good to know</h3><p>Pay online or at the front desk. A 10 percent sibling discount is available. Fees are non-refundable after the second class, but a batch transfer can be requested during the first two weeks.</p></div></div>", unsafe_allow_html=True)

elif page == "Events":
    page_header("Beyond the weekly class", "Come be part of the room.", "Performances, open studios, and workshops are where practice turns into shared memory.")
    for month, day, name, description, timing, price, image in EVENTS:
        left, middle, right = st.columns([1, 3, 2.3])
        with left:
            st.markdown(f"<div class='event-date'><span>{month}</span><strong>{day}</strong></div>", unsafe_allow_html=True)
        with middle:
            st.markdown(f"<div style='padding:.2rem 0 1.2rem 0'><h3 style='margin:0'>{name}</h3><p style='margin:.3rem 0;color:#746e66'>{description}</p><span class='meta'>{timing}</span></div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"<img src='{image}' alt='{name}' style='width:100%;height:115px;object-fit:cover;display:block;margin-bottom:.45rem'><div style='text-align:right;color:#1f7775;font-weight:700'>{price}</div>", unsafe_allow_html=True)
        st.divider()

elif page == "Admissions":
    page_header("Take the first step", "Join the community.", "Tell us a little about yourself. We will respond with the right batch, next orientation date, and a clear enrollment path.")
    left, right = st.columns([1.1, 1])
    with left:
        with st.form("admission_form"):
            name = st.text_input("Your name")
            phone = st.text_input("Phone number")
            location = st.text_input("Your area or city", placeholder="For example, Indiranagar")
            course = st.selectbox("Course you are curious about", [course["name"] for course in COURSES])
            experience = st.selectbox("Your dance experience", ["I am completely new", "Some informal experience", "I have trained before"])
            goals = st.text_area("What would you like to explore in dance?", placeholder="A few words about your dance goals...")
            submitted = st.form_submit_button("Request an orientation")
            if submitted:
                if not name:
                    st.error("Please add your name so we can register your request.")
                elif set(re.findall(r"[a-z0-9]+", f"{course} {experience} {goals}".lower())).intersection(NON_DANCER_TERMS):
                    st.error("Taalika admissions are only for dance training. Please describe your dance goals.")
                else:
                    result = api_request("POST", "/admissions", {"participant_type": "dancer", "name": name, "phone": phone, "location": location, "course": course, "experience": experience, "goals": goals})
                    if result:
                        st.success(f"Thank you, {name}. Your orientation request has been saved.")
                    else:
                        st.error("The academy service is currently unavailable. Please start the backend and submit again.")
    with right:
        st.markdown("<div class='panel'><div class='eyebrow'>What happens next</div><h3>Three small steps.</h3><p><strong>01 &nbsp; We reply</strong><br>Our team confirms the best orientation slot.</p><p><strong>02 &nbsp; You visit</strong><br>Meet your teacher and experience the studio.</p><p><strong>03 &nbsp; You begin</strong><br>Choose your batch and receive your welcome guide.</p></div>", unsafe_allow_html=True)

elif page == "Visit Us":
    page_header("The studio", "Find your way to the room.", "Taalika is a dancer-first space for practice, instruction, and performance. Come by for an orientation or a scheduled class.")
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown(f"<div class='panel'><div class='eyebrow'>Location</div><h3>{STUDIO_ADDRESS}</h3><p class='meta'>Monday to Saturday &nbsp;|&nbsp; 9:30 AM - 8:30 PM</p><p>Our studios are designed for focused practice, small batches, and individual feedback. Please contact the front desk before visiting for the first time.</p><a href='{MAP_URL}' target='_blank' style='color:#1f7775;font-weight:700'>Open directions in Google Maps &rarr;</a></div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='panel'><div class='eyebrow'>For dancers</div><h3>What to bring</h3><p>Wear comfortable clothing, bring water, and carry a notebook for practice notes. Heavy jewelry is best left at home.</p><p class='quote'>New to dance? Start with a free 30-minute orientation class.</p></div>", unsafe_allow_html=True)

elif page == "Ask Taalika":
    page_header("Studio guide", "Ask about your dance journey.", "This assistant searches the academy knowledge base for dancers and people exploring classes, schedules, fees, admissions, events, and the studio.")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for role, message in st.session_state.chat:
        with st.chat_message(role):
            st.write(message)
    question = st.chat_input("Try: What does the beginner course cost?")
    if question:
        st.session_state.chat.append(("user", question))
        result = api_request("POST", "/chat", {"question": question})
        answer = result["answer"] if result else answer_question(question)
        st.session_state.chat.append(("assistant", answer))
        st.rerun()
    st.markdown("<div class='section'><div class='eyebrow'>Popular questions</div></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for col, prompt in zip(cols, ["What are the beginner timings?", "Tell me about fee discounts.", "Can I join without experience?"]):
        with col:
            if st.button(prompt, use_container_width=True):
                st.session_state.chat.append(("user", prompt))
                result = api_request("POST", "/chat", {"question": prompt})
                answer = result["answer"] if result else answer_question(prompt)
                st.session_state.chat.append(("assistant", answer))
                st.rerun()

st.markdown("<div class='footer'>Taalika Dance Academy &nbsp; / &nbsp; 24 Lotus Lane, Indiranagar, Bengaluru &nbsp; / &nbsp; hello@taalika.example</div>", unsafe_allow_html=True)
