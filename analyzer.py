import os
import re
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Ініціалізація клієнта OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Language + market detection
# ---------------------------
def detect_language(text: str) -> str:
    """
    Very lightweight heuristic without extra deps:
    - If Cyrillic dominates -> 'uk' (treat as Ukrainian market target)
    - Else -> 'en'
    """
    if not text:
        return "en"

    cyr = len(re.findall(r"[А-Яа-яЁёІіЇїЄєҐґ]", text))
    lat = len(re.findall(r"[A-Za-z]", text))

    # If any distinctly Ukrainian letters present, force 'uk'
    if re.search(r"[ІіЇїЄєҐґ]", text):
        return "uk"

    if cyr > lat:
        return "uk"
    return "en"


def market_and_style(lang: str):
    """
    Returns (market_note, style_note, reply_language_note)
    - market_note: what market to optimize for
    - style_note: region-specific conventions
    - reply_language_note: instruction for output language
    """
    if lang == "uk":
        return (
            "Орієнтуйся на ринок праці України.",
            (
                "Враховуй звичні для України підходи до резюме (може бути 1–2 сторінки, "
                "обережно з особистими даними; сфокусуйся на досягненнях і релевантних навичках). "
                "Поясни, як підвищити ATS-сумісність українською. "
                "За потреби зазнач, як адаптувати формат/розділи відповідно до очікувань роботодавців в Україні."
            ),
            "Відповідай українською мовою.",
        )
    else:
        return (
            "Target the United Kingdom job market.",
            (
                "Use UK CV conventions (no photo/date of birth, concise bullet points, UK spelling, "
                "ATS-friendly formatting, clear impact metrics). "
                "If appropriate, reference UK norms (e.g., responsibilities vs achievements, tailored skills)."
            ),
            "Respond in English (UK).",
        )


# ---------------------------
# File reading
# ---------------------------
def extract_text_from_file(file_path):
    if file_path.lower().endswith(".pdf"):
        with fitz.open(file_path) as doc:
            return "\n".join([page.get_text() for page in doc])
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------
# Helpers
# ---------------------------
def safe_take(s: str, max_chars: int = 120_000) -> str:
    """Simple guard to avoid extremely long inputs (keeps prompts snappy)."""
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n\n[...truncated for processing...]"


async def _ask_gpt(prompt: str) -> str:
    resp = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip() if resp.choices else "❌ GPT did not return a valid response."


# ---------------------------
# 🔍 CV analysis
# ---------------------------
async def analyze_resume(file_path):
    content = safe_take(extract_text_from_file(file_path))
    lang = detect_language(content)
    market_note, style_note, reply_lang = market_and_style(lang)

    prompt = f"""
You are a professional career consultant with 10+ years of experience in HR and CV coaching.
{market_note}
{style_note}
{reply_lang}

Analyze the following resume as if the candidate is applying for a modern, competitive role.

Your tasks:
1) Give a clear overall impression (1–2 sentences).
2) Evaluate each section separately:
   - Summary/Profile (Загальний аналіз)
   - Skills/Qualifications (Ключові навички/Кваліфікація)
   - Experience (use metrics wherever possible) (Досвід)
   - Education (Освіта)
   - Formatting & ATS-readiness (Формат&Оцінка готовності)
3) For every issue, provide a concrete suggestion AND an improved wording the candidate can copy.
4) Finish with a one-paragraph “ideal rewritten summary” for this resume, aligned with the target market above.

CV:
{content}
"""
    return await _ask_gpt(prompt)


# ---------------------------
# 🎯 CV and job match analysis
# ---------------------------
async def analyze_for_vacancy(vacancy_text, resume_text):
    vacancy_text = safe_take(vacancy_text)
    resume_text = safe_take(resume_text)

    lang = detect_language(resume_text or vacancy_text)
    market_note, style_note, reply_lang = market_and_style(lang)

    prompt = f"""
You're a senior recruiter helping a candidate tailor their CV for a specific job.
{market_note}
{style_note}
{reply_lang}

Below is a job description and the candidate’s current CV. Your job:
1) Identify key hard and soft skills from the vacancy (prioritize those relevant to the target market).
2) Map them to the candidate's experience (point to concrete evidence).
3) Write a new personalized profile paragraph the candidate can paste into their CV.
4) Provide 4–6 bullet points tailored to the vacancy for the Experience section (achievement-focused, ATS-friendly).
5) List unmet requirements and actionable ways to address them (certs, projects, learning paths).

📌 Job Vacancy:
{vacancy_text}

📄 Candidate's CV:
{resume_text}
"""
    return await _ask_gpt(prompt)


# ---------------------------
# 🧠 HR Expert Advice
# ---------------------------
async def give_hr_feedback(resume_text):
    resume_text = safe_take(resume_text)
    lang = detect_language(resume_text)
    market_note, style_note, reply_lang = market_and_style(lang)

    prompt = f"""
Imagine you're a senior HR specialist providing a deep consultation to improve this resume.
{market_note}
{style_note}
{reply_lang}

Provide a full audit under these sections:
1) Format & Layout
2) Tone & Wording
3) Achievements (metrics, results, impact)
4) Focus (relevance, clarity of message)
5) Suggestions (what to restructure, cut, or emphasize)

For each issue:
- Briefly explain why it matters for the {('UK' if lang=='en' else 'Ukrainian')} market
- Provide a concrete revision or rephrased example the candidate can paste

Finish with:
- A competitiveness score out of 10 (for the target market)
- A 3–5 line action plan for the next edit iteration

CV:
{resume_text}
"""
    return await _ask_gpt(prompt)


# ---------------------------
# 💌 Generate Cover Letter
# ---------------------------
async def generate_cover_letter(vacancy_text, resume_text):
    vacancy_text = safe_take(vacancy_text)
    resume_text = safe_take(resume_text)

    lang = detect_language(resume_text or vacancy_text)
    market_note, style_note, reply_lang = market_and_style(lang)

    prompt = f"""
You are an expert in writing winning cover letters that blend personality and professionalism.
{market_note}
{style_note}
{reply_lang}

Write a tailored, job-specific cover letter based on:
- the job description
- the candidate’s resume
- the target company context (infer from vacancy if needed)

Structure:
1) Intro — clear interest in role & company
2) Why this company — values/mission/goals alignment (UK/UA market expectations as relevant)
3) Why this candidate — 2–3 concrete, metric-backed achievements
4) Close — enthusiasm + call to interview

Tone: confident, polite, modern.
Length: up to 300 words, clear paragraphs.

📌 Job Vacancy:
{vacancy_text}

📄 Candidate's CV:
{resume_text}
"""
    return await _ask_gpt(prompt)
