# CVise Telegram Bot Project (Sensitive check in all modes)

# --- analyzer.py (final unified detection) ---
import os
import re
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Language + market detection
# ---------------------------
def detect_language(text: str) -> str:
    if not text:
        return "en"
    cyr = len(re.findall(r"[А-Яа-яЁёІіЇїЄєҐґ]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    if re.search(r"[ІіЇїЄєҐґ]", text):
        return "uk"
    return "uk" if cyr > lat else "en"

def market_and_style(lang: str):
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
    ext = file_path.lower()
    if ext.endswith(".pdf"):
        with fitz.open(file_path) as doc:
            return "\n".join([page.get_text() for page in doc])
    elif ext.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"[❌ Error reading DOCX file: {e}]"
    else:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[❌ Error reading TXT file: {e}]"

# ---------------------------
# Helpers
# ---------------------------
def safe_take(s: str, max_chars: int = 120_000) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + "\n\n[...truncated for processing...]"

def detect_sensitive_elements(text: str, lang: str) -> str:
    warnings = []
    if lang == "en":
        if re.search(r"(photo|photograph|image|picture)", text, re.IGNORECASE):
            warnings.append("⚠️ The CV appears to reference a photo. In the UK, including photos is discouraged.")
        if re.search(r"date of birth|DOB|birth date", text, re.IGNORECASE):
            warnings.append("⚠️ Date of birth detected. Avoid including it in UK CVs.")
        if re.search(r"marital status|gender|nationality", text, re.IGNORECASE):
            warnings.append("⚠️ Personal data like marital status or gender should not appear on UK CVs.")
    return "\n".join(warnings)

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
    sensitive_issues = detect_sensitive_elements(content, lang)

    prompt = f"""
You are a professional career consultant with 10+ years of experience in HR and CV coaching.
{market_note}
{style_note}
{reply_lang}

Analyze the following resume as if the candidate is applying for a modern, competitive role.

Your tasks:
1) Give a clear overall impression (1–2 sentences).
2) Evaluate each section separately:
   - Summary/Profile
   - Skills/Qualifications
   - Experience (use metrics wherever possible)
   - Education
   - Formatting & ATS-readiness
3) For every issue, provide a concrete suggestion AND an improved wording the candidate can copy.
4) Finish with a one-paragraph “ideal rewritten summary” for this resume, aligned with the target market above.

Resume:
{content}
"""
    response = await _ask_gpt(prompt)
    return f"{sensitive_issues}\n\n{response}" if sensitive_issues else response

# ---------------------------
# 🎯 CV and job match analysis
# ---------------------------
async def analyze_for_vacancy(vacancy_text, resume_text):
    vacancy_text = safe_take(vacancy_text)
    resume_text = safe_take(resume_text)
    lang = detect_language(resume_text or vacancy_text)
    market_note, style_note, reply_lang = market_and_style(lang)
    sensitive_issues = detect_sensitive_elements(resume_text, lang)

    prompt = f"""
You're a senior recruiter helping a candidate tailor their CV for a specific job.
{market_note}
{style_note}
{reply_lang}

Below is a job description and the candidate’s current CV. Your job:
1) Identify key hard and soft skills from the vacancy.
2) Map them to the candidate's experience.
3) Write a personalized profile paragraph.
4) Suggest 4–6 tailored bullet points for Experience.
5) List gaps and how to address them.

📌 Job Vacancy:
{vacancy_text}
📄 Candidate's CV:
{resume_text}
"""
    response = await _ask_gpt(prompt)
    return f"{sensitive_issues}\n\n{response}" if sensitive_issues else response

# ---------------------------
# 🧠 HR Expert Advice
# ---------------------------
async def give_hr_feedback(resume_text):
    resume_text = safe_take(resume_text)
    lang = detect_language(resume_text)
    market_note, style_note, reply_lang = market_and_style(lang)
    sensitive_issues = detect_sensitive_elements(resume_text, lang)

    prompt = f"""
Imagine you're a senior HR specialist providing a deep consultation to improve this resume.
{market_note}
{style_note}
{reply_lang}

Provide a full audit under these sections:
1) Format & Layout
2) Tone & Wording
3) Achievements (metrics, results, impact)
4) Focus (relevance, clarity)
5) Suggestions (what to restructure or cut)

For each issue:
- Explain its relevance for the {'UK' if lang=='en' else 'Ukrainian'} market
- Provide a rephrased example

Finish with:
- Competitiveness score out of 10
- 3–5 line action plan

CV:
{resume_text}
"""
    response = await _ask_gpt(prompt)
    return f"{sensitive_issues}\n\n{response}" if sensitive_issues else response

# ---------------------------
# 💌 Generate Cover Letter
# ---------------------------
async def generate_cover_letter(vacancy_text, resume_text):
    vacancy_text = safe_take(vacancy_text)
    resume_text = safe_take(resume_text)
    lang = detect_language(resume_text or vacancy_text)
    market_note, style_note, reply_lang = market_and_style(lang)
    sensitive_issues = detect_sensitive_elements(resume_text, lang)

    prompt = f"""
You are an expert in writing winning cover letters.
{market_note}
{style_note}
{reply_lang}

Write a tailored cover letter based on:
- the job description
- the resume
- the company context (infer if needed)

Structure:
1) Intro — interest in role & company
2) Why this company — alignment with values
3) Why this candidate — 2–3 metric-backed achievements
4) Close — enthusiasm + CTA

Tone: confident, modern. Length: up to 300 words.

📌 Job Vacancy:
{vacancy_text}
📄 Candidate's CV:
{resume_text}
"""
    response = await _ask_gpt(prompt)
    return f"{sensitive_issues}\n\n{response}" if sensitive_issues else response
