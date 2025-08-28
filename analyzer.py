import os
import re
import fitz  # PyMuPDF
import datetime
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SECTION_KEYS = {
    "summary/profile": "sum",
    "skills/qualifications": "skills",
    "experience": "exp",
    "education": "edu",
    "formatting & ats": "fmt"
}

SECTION_LABELS = {v: k.title() for k, v in SECTION_KEYS.items()}

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

🌟 Overall Score: XX / 100

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
    gpt_response = await _ask_gpt(prompt)
    full_response = f"{proactive_warning}\n\n{gpt_response}" if proactive_warning else gpt_response

    # 🧠 Розбір GPT-відповіді
    user_data = parse_gpt_output(full_response)

    # 📄 Створення PDF
    output_path = build_output_path("user", "cv_analysis")
    render_html_to_pdf(user_data, output_path)

    return full_response, output_path


# Інші функції (analyze_for_vacancy, give_hr_feedback, generate_cover_letter, step_by_step_review) додаються за потреби.


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

🌟 Overall Score: XX / 100

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

🌟 Overall Score: XX / 100

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
    content = safe_take(extract_text_from_file(file_path))
    lang = detect_language(content)
    market_note, style_note, reply_lang = market_and_style(lang)

    prompt = f"""
You are a professional CV coach.
{market_note}
{style_note}
{reply_lang}

Do a **step-by-step** interactive CV review. After each section:
- Give short feedback.
- Use this wording: \n\n\"Would you like to edit this section now?\"
- Use clear labels:
  1. **Summary/Profile**
  2. **Skills/Qualifications**
  3. **Experience**
  4. **Education**
  5. **Formatting & ATS**

Important:
- End each section with these inline buttons:
  [Edit ✏️] (callback_data: edit_KEY)
  [Skip ⏭️] (callback_data: skip_KEY)
- Use Markdown formatting for headings and bullet points.

Resume:
{content}
"""
    response = await _ask_gpt(prompt)
    sections = response.split("\n\n")

    parsed_sections = []
    for block in sections:
        header = block.split("\n", 1)[0].lower().strip("* ")
        key = SECTION_KEYS.get(header)
        if key:
            parsed_sections.append((key, header.title(), block.strip()))

    output_path = build_output_path("user", "step_by_step")
    generate_pdf_report(response, output_path)
    return parsed_sections, output_path

def edit_section(section_name: str, current_text: str) -> str:
    prompt = (
        f"Please improve the following section of a CV. Keep it concise and professional. "
        f"Only rewrite the text, do not return explanations.\n\nSection: {section_name}\n\n{current_text}"
    )
    return prompt
import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
def parse_gpt_output(gpt_text: str) -> dict:
    """
    Парсить текстову відповідь GPT у формат user_data для HTML-шаблону.
    """
    lines = gpt_text.strip().splitlines()
    data = {
        'name': '',
        'summary': '',
        'sections': [],
        'overall_score': 0,
        'recommendations': [],
    }

    current_section = None
    buffer = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("📊 CV Score Breakdown:"):
            current_section = "scores"
            continue
        elif line.startswith("🌟 Overall Score:"):
            match = re.search(r'(\d+)', line)
            if match:
                data["overall_score"] = int(match.group(1))
            continue
        elif line.startswith("📌"):
            current_section = "recommendations"
            continue

        if current_section == "scores":
            match = re.match(r"•\s*(.+?):\s*(\d+)", line)
            if match:
                title = match.group(1).strip()
                score = int(match.group(2))
                data["sections"].append({
                    "title": title,
                    "score": score,
                    "feedback": ""
                })

        elif current_section == "recommendations":
            data["recommendations"].append(line.strip("• ").strip("- ").strip())

        else:
            if data["summary"] == "":
                data["summary"] = line
            else:
                buffer.append(line)

    # Заповнення фідбеку з буфера (якщо GPT не розділяв чітко по секціях)
    if buffer and data["sections"]:
        chunk_size = max(1, len(buffer) // len(data["sections"]))
        for i, section in enumerate(data["sections"]):
            section["feedback"] = "\n".join(buffer[i*chunk_size:(i+1)*chunk_size]).strip()

    return data


def render_html_to_pdf(user_data: dict, output_path: str):
    """
    user_data = {
        'name': 'John Doe',
        'summary': 'Experienced Project Manager...',
        'sections': [
            {'title': 'Summary/Profile', 'score': 7, 'feedback': 'Try to personalize...'},
            {'title': 'Skills & Qualifications', 'score': 8, 'feedback': 'Strong technical skills...'},
            {'title': 'Experience', 'score': 6, 'feedback': 'Quantify your achievements...'},
            {'title': 'Education', 'score': 9, 'feedback': 'Well-detailed and relevant.'},
            {'title': 'Formatting & ATS', 'score': 5, 'feedback': 'Avoid tables and columns...'}
        ],
        'overall_score': 70,
        'recommendations': [
            'Use action verbs.',
            'Include metrics in experience.',
            'Tailor the CV for each application.'
        ]
    }
    """
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report_template.html")
    html_out = template.render(data=user_data, now=datetime.now())

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    HTML(string=html_out).write_pdf(output_path)
    return output_path