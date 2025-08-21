# --- analyzer.py (UPDATED: all 5 modes including Step-by-step review) ---

import os
import re
import fitz  # PyMuPDF
import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def safe_take(s: str, max_chars: int = 120_000) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + "\n\n[...truncated for processing...]"

def universal_uk_warning(lang: str) -> str:
    if lang == "en":
        return (
            "⚠️ Note: If your CV includes a photo or personal data such as date of birth, gender, or marital status, "
            "we recommend removing them for applications in the UK job market."
        )
    return ""

async def _ask_gpt(prompt: str) -> str:
    resp = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip() if resp.choices else "❌ GPT did not return a valid response."

def generate_pdf_report(text: str, output_path: str):
    styles = getSampleStyleSheet()
    story = []
    for part in text.split("\n\n"):
        story.append(Paragraph(part.strip().replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 12))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    doc.build(story)
    return output_path

def build_output_path(user_id: str, prefix: str = "report") -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"results/{user_id}/{prefix}_{ts}.pdf"

def _build_full_prompt(content: str, market_note: str, style_note: str, reply_lang: str) -> str:
    return f"""
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
5) Rate the following categories from 1 to 10:
   • Summary/Profile
   • Skills & Qualifications
   • Experience
   • Education
   • Formatting & ATS-readiness
6) Then, calculate the average score and present it clearly like this:

📊 CV Score Breakdown:
• Summary/Profile: X / 10
• Skills & Qualifications: X / 10
• Experience: X / 10
• Education: X / 10
• Formatting & ATS: X / 10

🎯 Overall Score: XX / 100

7) Based on lowest scoring areas, provide 3–5 actionable recommendations.

Resume:
{content}
"""

async def analyze_resume(file_path):
    content = safe_take(extract_text_from_file(file_path))
    lang = detect_language(content)
    market_note, style_note, reply_lang = market_and_style(lang)
    proactive_warning = universal_uk_warning(lang)

    prompt = _build_full_prompt(content, market_note, style_note, reply_lang)
    response = await _ask_gpt(prompt)
    full_response = f"{proactive_warning}\n\n{response}" if proactive_warning else response

    output_path = build_output_path("user", "cv_analysis")
    generate_pdf_report(full_response, output_path)
    return full_response, output_path

async def analyze_for_vacancy(resume_path, vacancy_text):
    resume_content = safe_take(extract_text_from_file(resume_path))
    lang = detect_language(resume_content)
    market_note, style_note, reply_lang = market_and_style(lang)
    proactive_warning = universal_uk_warning(lang)

    prompt = f"""
You are a senior HR consultant and career advisor with expertise in aligning CVs to job roles.
{market_note}
{style_note}
{reply_lang}

Task:
- Compare the following resume to the job vacancy.
- Identify alignment and gaps.
- Recommend edits to make the CV a better match (especially in skills and experience).
- Rephrase or add bullet points to fit the job.
- Evaluate formatting and language alignment with market expectations.
- At the end, rate the resume by categories and provide an overall score, just like this:

📊 CV Score Breakdown:
• Summary/Profile: X / 10
• Skills & Qualifications: X / 10
• Experience: X / 10
• Education: X / 10
• Formatting & ATS: X / 10

🎯 Overall Score: XX / 100

📌 Recommend 3–5 actions to increase alignment and success.

---
Resume:
{resume_content}

---
Job Vacancy:
{vacancy_text}
"""
    response = await _ask_gpt(prompt)
    full_response = f"{proactive_warning}\n\n{response}" if proactive_warning else response
    output_path = build_output_path("user", "cv_match")
    generate_pdf_report(full_response, output_path)
    return full_response, output_path

async def give_hr_feedback(resume_path):
    content = safe_take(extract_text_from_file(resume_path))
    lang = detect_language(content)
    market_note, style_note, reply_lang = market_and_style(lang)
    proactive_warning = universal_uk_warning(lang)

    prompt = f"""
You are a professional career coach helping job seekers improve their CVs.
{market_note}
{style_note}
{reply_lang}

Provide a brief but focused HR-style critique of this CV:
- What is strong?
- What is missing?
- Formatting and clarity issues
- Suggestions to improve effectiveness for the job market above

Rate the resume using:
📊 CV Score Breakdown:
• Summary/Profile: X / 10
• Skills & Qualifications: X / 10
• Experience: X / 10
• Education: X / 10
• Formatting & ATS: X / 10

🎯 Overall Score: XX / 100

📌 List 3–5 practical improvement tips.

Resume:
{content}
"""
    response = await _ask_gpt(prompt)
    full_response = f"{proactive_warning}\n\n{response}" if proactive_warning else response
    output_path = build_output_path("user", "hr_feedback")
    generate_pdf_report(full_response, output_path)
    return full_response, output_path

async def generate_cover_letter(vacancy_text, resume_text):
    prompt = f"""
You are an experienced UK-based hiring manager helping candidates generate strong, personalised cover letters.
Match the applicant's CV to the vacancy and write a professional, persuasive letter that:
- Starts with a strong opening
- Explains how the candidate fits the role (skills, experience, results)
- Ends with a call to action

Write in British English and keep it to 3 paragraphs.

---
Job Vacancy:
{vacancy_text}

---
Resume:
{resume_text}
"""
    response = await _ask_gpt(prompt)
    output_path = build_output_path("user", "cover_letter")
    generate_pdf_report(response, output_path)
    return response, output_path

async def step_by_step_review(file_path):
    async def _run():
        content = safe_take(extract_text_from_file(file_path))
        lang = detect_language(content)
        market_note, style_note, reply_lang = market_and_style(lang)

        prompt = f"""
You are a senior career coach.
{market_note}
{style_note}
{reply_lang}

Perform a **step-by-step** CV review.
- Review and comment each section one-by-one.
- Ask the user if they would like to edit/improve that section.
- Then move to the next section.

Sections:
1. Summary/Profile
2. Skills/Qualifications
3. Experience
4. Education
5. Formatting & ATS

Include practical improvement suggestions and examples.
Resume:
{content}
"""
        response = await _ask_gpt(prompt)
        full_response = response
        output_path = build_output_path("user", "step_by_step")
        generate_pdf_report(full_response, output_path)
        return full_response, output_path

    return await _run()
