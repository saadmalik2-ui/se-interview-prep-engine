import streamlit as st
import anthropic
import os
import sqlite3
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SE Interview Prep Engine",
    page_icon="🎯",
    layout="wide",
)

# ── Database setup ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("prep_history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            question TEXT,
            situation INTEGER,
            task INTEGER,
            action INTEGER,
            result INTEGER,
            total INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_score(question, situation, task, action, result, total):
    conn = sqlite3.connect("prep_history.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (date, question, situation, task, action, result, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), question, situation, task, action, result, total))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect("prep_history.db")
    c = conn.cursor()
    c.execute("SELECT date, question, situation, task, action, result, total FROM sessions ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_weak_points():
    conn = sqlite3.connect("prep_history.db")
    c = conn.cursor()
    c.execute("SELECT AVG(situation), AVG(task), AVG(action), AVG(result), COUNT(*) FROM sessions")
    row = c.fetchone()
    conn.close()
    return row

def clear_history():
    conn = sqlite3.connect("prep_history.db")
    c = conn.cursor()
    c.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()

def parse_scores(feedback_text):
    situation = re.search(r'\*\*Situation\*\*.*?(\d+)/25', feedback_text)
    task = re.search(r'\*\*Task\*\*.*?(\d+)/25', feedback_text)
    action = re.search(r'\*\*Action\*\*.*?(\d+)/25', feedback_text)
    result = re.search(r'\*\*Result\*\*.*?(\d+)/25', feedback_text)
    total = re.search(r'\*\*Total\*\*.*?(\d+)/100', feedback_text)
    if all([situation, task, action, result, total]):
        return (
            int(situation.group(1)),
            int(task.group(1)),
            int(action.group(1)),
            int(result.group(1)),
            int(total.group(1))
        )
    return None

init_db()

# ── API Key ───────────────────────────────────────────────────────────────────
st.title("🎯 SE Interview Prep Engine")
st.caption("Two modes: STAR Practice for behavioral questions. Deep Prep for full SE interview coverage.")

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key:
    api_key = st.text_input(
        "🔑 Paste your Anthropic API Key to get started",
        type="password",
        placeholder="sk-ant-...",
    )
if not api_key:
    st.info("Enter your API key above to continue.")
    st.stop()

client = anthropic.Anthropic(api_key=api_key)

def call_claude(prompt: str, max_tokens: int = 2000) -> str:
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

# ── Mode selector ─────────────────────────────────────────────────────────────
st.divider()
mode = st.radio(
    "Choose your prep mode:",
    ["⭐ STAR Practice — Behavioral questions + grading", "🧠 Deep Prep — Full SE interview coverage"],
    horizontal=True,
)

# ═════════════════════════════════════════════════════════════════════════════
# MODE 1 — STAR PRACTICE (original flow)
# ═════════════════════════════════════════════════════════════════════════════
if "STAR Practice" in mode:

    # Weak point summary
    st.divider()
    weak = get_weak_points()
    if weak and weak[4] and weak[4] >= 3:
        avg_s, avg_t, avg_a, avg_r, count = weak
        scores = {
            "Situation": avg_s or 0,
            "Task": avg_t or 0,
            "Action": avg_a or 0,
            "Result": avg_r or 0
        }
        weakest = min(scores, key=scores.get)
        weakest_score = scores[weakest]
        focus_map = {
            "Situation": "Set the scene clearly — who, what, when, and why it mattered.",
            "Task": "Be explicit about YOUR specific responsibility and what success looked like.",
            "Action": "Go deeper on what YOU specifically did — steps, decisions, tools used.",
            "Result": "Always end with a measurable outcome — numbers, percentages, business impact."
        }
        st.subheader("📌 Your Focus Area")
        st.warning(
            f"Based on your last {count} sessions, your weakest area is **{weakest}** "
            f"(avg {weakest_score:.0f}/25).\n\n"
            f"**Focus:** {focus_map[weakest]}"
        )

    # Step 1
    st.divider()
    st.subheader("Step 1 — Paste Your Context")
    col1, col2, col3 = st.columns(3)
    with col1:
        resume = st.text_area("📄 Your Resume", placeholder="Paste your resume here...", height=250)
    with col2:
        job_desc = st.text_area("💼 Job Description", placeholder="Paste the job description here...", height=250)
    with col3:
        interview_notes = st.text_area("🗒️ Interview Notes (optional)", placeholder="Any notes about the role, company, or interviewer...", height=250)

    # Step 2
    st.divider()
    st.subheader("Step 2 — Generate Likely Interview Questions")
    if "questions" not in st.session_state:
        st.session_state.questions = []

    if st.button("✨ Generate Questions", type="primary", disabled=not (resume and job_desc)):
        with st.spinner("Generating questions..."):
            weak_focus = ""
            if weak and weak[4] and weak[4] >= 3:
                scores = {"Situation": weak[0] or 0, "Task": weak[1] or 0, "Action": weak[2] or 0, "Result": weak[3] or 0}
                weakest = min(scores, key=scores.get)
                weak_focus = f"\nThis candidate struggles with {weakest} in their answers. Include questions that specifically require strong {weakest} responses."

            prompt = f"""
You are an expert Sales Engineering interviewer.

Based on the resume, job description, and any notes below, generate 8 realistic behavioral interview questions this candidate is VERY likely to be asked.

Focus on STAR-structured behavioral questions. Number each question.
{weak_focus}

RESUME:
{resume}

JOB DESCRIPTION:
{job_desc}

INTERVIEW NOTES:
{interview_notes or "None provided."}

Return ONLY the numbered list of questions. No preamble or explanation.
"""
            raw = call_claude(prompt, max_tokens=800)
            lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
            st.session_state.questions = [l for l in lines if l[0].isdigit()]

    if st.session_state.questions:
        st.success(f"Generated {len(st.session_state.questions)} questions!")
        for q in st.session_state.questions:
            st.markdown(f"- {q}")

    # Step 3
    st.divider()
    st.subheader("Step 3 — Answer a Question & Get Feedback")
    selected_q = st.selectbox(
        "Choose a question to answer:",
        options=["— select one —"] + (st.session_state.questions if st.session_state.questions else []),
    )
    user_answer = st.text_area("✍️ Your Answer", placeholder="Type your answer here...", height=200)

    if "feedback" not in st.session_state:
        st.session_state.feedback = None

    ready = (selected_q != "— select one —" and user_answer.strip() and resume and job_desc)

    if st.button("🔍 Grade My Answer", type="primary", disabled=not ready):
        with st.spinner("Analysing your answer..."):
            prompt = f"""
You are an expert Sales Engineering interview coach.

The candidate is interviewing for this role:
{job_desc}

Their resume:
{resume}

They were asked this question:
{selected_q}

Their answer:
{user_answer}

Evaluate the answer using the STAR framework (Situation, Task, Action, Result).

Return your response in this EXACT format:

## STAR Score

**Situation** (0-25): <score>/25 — <one line of feedback>
**Task** (0-25): <score>/25 — <one line of feedback>
**Action** (0-25): <score>/25 — <one line of feedback>
**Result** (0-25): <score>/25 — <one line of feedback>
**Total**: <total>/100

---

## Direct Feedback

<3-5 sentences of honest, direct coaching. What's missing? What's weak? What landed well?>

---

## Stronger Version

<Rewrite the answer in first person, 150-200 words, fully structured with STAR, tailored to the job description. Make it punchy and memorable.>

---

## Follow-Up Questions

<List 3 follow-up questions an interviewer might ask after this answer.>
"""
            st.session_state.feedback = call_claude(prompt, max_tokens=1500)
            if st.session_state.feedback:
                scores = parse_scores(st.session_state.feedback)
                if scores:
                    save_score(selected_q, scores[0], scores[1], scores[2], scores[3], scores[4])

    if st.session_state.feedback:
        st.divider()
        st.subheader("📊 Feedback")
        st.markdown(st.session_state.feedback)

    # Progress history
    history = get_history()
    if history:
        st.divider()
        st.subheader("📈 Your Progress History")
        for row in history:
            date, question, s, t, a, r, total = row
            short_q = question[:80] + "..." if len(question) > 80 else question
            color = "🟢" if total >= 70 else "🟡" if total >= 50 else "🔴"
            st.markdown(f"{color} **{total}/100** — {short_q} _{date}_")
        if st.button("🗑️ Clear History"):
            clear_history()
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# MODE 2 — DEEP PREP
# ═════════════════════════════════════════════════════════════════════════════
else:

    st.divider()
    st.subheader("Step 1 — Paste Your Context")
    col1, col2, col3 = st.columns(3)
    with col1:
        dp_resume = st.text_area("📄 Your Resume", placeholder="Paste your resume here...", height=250, key="dp_resume")
    with col2:
        dp_job_desc = st.text_area("💼 Job Description", placeholder="Paste the job description here...", height=250, key="dp_jd")
    with col3:
        dp_notes = st.text_area("🗒️ Interview Notes (optional)", placeholder="Interviewer name, company context, known gaps...", height=250, key="dp_notes")

    # Question type toggles
    st.divider()
    st.subheader("Step 2 — Choose Your Question Types")

    col1, col2, col3 = st.columns(3)
    with col1:
        do_behavioral = st.checkbox("⭐ Behavioral / STAR", value=True)
        do_domain = st.checkbox("🏭 Domain Knowledge", value=True)
    with col2:
        do_discovery = st.checkbox("🔍 Discovery Questions", value=True)
        do_objection = st.checkbox("🛡️ Objection Handling", value=True)
    with col3:
        do_technical = st.checkbox("⚙️ Technical Translation", value=True)
        do_executive = st.checkbox("📊 Executive / Business", value=True)

    # Number of questions per type
    st.divider()
    st.subheader("Step 3 — How Many Per Type?")
    num_q = st.slider("Questions per type", min_value=3, max_value=10, value=5)

    # Generate
    st.divider()
    selected_types = []
    if do_behavioral: selected_types.append("Behavioral / STAR")
    if do_domain: selected_types.append("Domain Knowledge")
    if do_discovery: selected_types.append("Discovery Questions")
    if do_objection: selected_types.append("Objection Handling")
    if do_technical: selected_types.append("Technical Translation")
    if do_executive: selected_types.append("Executive / Business Impact")

    if "deep_questions" not in st.session_state:
        st.session_state.deep_questions = None

    can_generate = dp_resume and dp_job_desc and len(selected_types) > 0

    if st.button("🧠 Generate Deep Prep Questions", type="primary", disabled=not can_generate):
        with st.spinner(f"Generating {num_q} questions across {len(selected_types)} categories..."):

            types_instruction = ""
            for t in selected_types:
                if t == "Behavioral / STAR":
                    types_instruction += f"""
### Behavioral / STAR ({num_q} questions)
Generate {num_q} behavioral questions that require structured STAR answers about past experience.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""
                elif t == "Domain Knowledge":
                    types_instruction += f"""
### Domain Knowledge ({num_q} questions)
Generate {num_q} questions testing industry and product domain knowledge specific to this role and company.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""
                elif t == "Discovery Questions":
                    types_instruction += f"""
### Discovery Questions ({num_q} questions)
Generate {num_q} questions about how the candidate runs discovery calls, qualifies opportunities, and uncovers customer pain.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""
                elif t == "Objection Handling":
                    types_instruction += f"""
### Objection Handling ({num_q} questions)
Generate {num_q} questions about how the candidate handles customer objections, competitive situations, and pushback.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""
                elif t == "Technical Translation":
                    types_instruction += f"""
### Technical Translation ({num_q} questions)
Generate {num_q} questions that test the candidate's ability to explain complex technical concepts simply to different audiences.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""
                elif t == "Executive / Business Impact":
                    types_instruction += f"""
### Executive / Business Impact ({num_q} questions)
Generate {num_q} questions about business impact, ROI, executive communication, and commercial thinking.
For each question add on a new line: WHY: <one sentence explaining why the interviewer asks this>
"""

            prompt = f"""
You are an expert Sales Engineering hiring manager conducting a comprehensive interview.

Based on the candidate's resume, job description, and any notes below — generate interview questions across the requested categories.

RESUME:
{dp_resume}

JOB DESCRIPTION:
{dp_job_desc}

INTERVIEW NOTES:
{dp_notes or "None provided."}

Generate questions in this EXACT structure. Use the exact section headers shown.
After each question include WHY: on a new line explaining why an interviewer asks it.

{types_instruction}

Be specific to this candidate's background and this company's domain. Do not generate generic questions.
"""
            st.session_state.deep_questions = call_claude(prompt, max_tokens=4000)

    # Display deep prep results
    if st.session_state.deep_questions:
        st.divider()
        st.subheader("📋 Your Deep Prep Questions")
        st.markdown(st.session_state.deep_questions)

        # Download button
        st.download_button(
            label="⬇️ Download as text file",
            data=st.session_state.deep_questions,
            file_name=f"deep_prep_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )

        if st.button("🗑️ Clear Questions", key="clear_deep"):
            st.session_state.deep_questions = None
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with Streamlit + Anthropic Claude · SE Interview Prep Engine v2")
