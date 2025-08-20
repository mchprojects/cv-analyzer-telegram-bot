import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Ініціалізація клієнта OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Читання PDF або TXT
def extract_text_from_file(file_path):
    if file_path.lower().endswith(".pdf"):
        with fitz.open(file_path) as doc:
            return "\n".join([page.get_text() for page in doc])
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# 🔍 Розбір резюме
async def analyze_resume(file_path):
    content = extract_text_from_file(file_path)
    prompt = f"""
You are a professional career consultant with 10+ years of experience in HR and CV coaching. 
Please analyze the following resume **as if the candidate is applying for a modern, competitive role in general**.
Your task:
1. Give a clear summary of your impression (1–2 sentences).
2. Evaluate the following sections separately:
- 🔍 Summary Review
- 💼 Skills/Qualifications
- 📈 Experience (include use of metrics)
- 🎓 Education
- 🌐 Formatting & ATS-readiness
3. For each issue, give a concrete suggestion and an **improved formulation** the candidate can use.
4. End with a 1-paragraph version of an ideal rewritten summary for this resume.
Be practical and copyable – write in a clear, natural tone.

CV:
{content}
"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# 🎯 Порівняння резюме з вакансією
async def analyze_for_vacancy(vacancy_text, resume_text):
    prompt = f"""
You're a senior recruiter helping a candidate tailor their CV for a specific job.

Below is a job description and the candidate’s current CV. Your job:
1. Identify key hard and soft skills from the vacancy.
2. Match them with the candidate's experience.
3. Write a new **personalized profile paragraph** the candidate can paste into their CV.
4. Create 4–6 bullet points the candidate can add to the 'Experience' section to better match the vacancy.
5. Highlight which **requirements are not met** and how they can improve them (e.g., via certificates or new experience).
🎯 Goal: Create optimized, human-sounding results for pasting into a CV or cover letter.

📌 Job Vacancy:
{vacancy_text}

📄 Candidate's CV:
{resume_text}
"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# 🧠 Консультація від HR
async def give_hr_feedback(resume_text):
    prompt = f"""
Imagine you're a senior HR specialist providing a detailed consultation for improving this resume.
Your task is to provide a full audit of the CV below under the following sections:
1. 📋 Format & Layout
2. ✍️ Tone & Wording
3. ✅ Achievements (metrics, results, impact)
4. 🎯 Focus (relevance, clarity of message)
5. 📍 Suggestions (restructure, cut, emphasize)

For each issue – give:
- a short explanation
- a **concrete revision or rephrased example**

Finish with a final score out of 10 for competitiveness.

CV:
{resume_text}
"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# 💌 Генерація супровідного листа
async def generate_cover_letter(vacancy_text, resume_text):
    prompt = f"""
You are an expert in writing winning cover letters that combine personality with professionalism.

Write a **tailored, job-specific cover letter** based on:
- the job description
- the candidate’s resume
- the target company

Use this structure:
1. Intro: Express interest in role & company.
2. Body 1: Why this company – values, mission, goals.
3. Body 2: Why this candidate – achievements, experience.
4. Close: Show enthusiasm + request for interview.

📌 Tone: confident, polite, modern.
📌 Length: up to 300 words, clear paragraphs.

📌 Job Vacancy:
{vacancy_text}

📄 Candidate's CV:
{resume_text}
"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()
