##### 📘 README.md

##### \# CVise — Telegram Bot for CV Analysis

##### 

##### CVise is an AI-powered Telegram bot that helps users analyze, improve, and tailor their resumes (CVs) for specific job markets (UK or Ukraine). It supports resume feedback, job match alignment, HR consultation, and personalized cover letter generation.

##### 

##### \## ✨ Features

##### 

##### \- 📄 \*\*CV Analysis\*\* — Get section-by-section feedback on your resume.

##### \- 🎯 \*\*CV and Job Match\*\* — Match your resume against a job vacancy.

##### \- 🧠 \*\*HR Expert Advice\*\* — Receive professional suggestions from an HR-style prompt.

##### \- 💌 \*\*Generate Cover Letter\*\* — Automatically write a personalized cover letter.

##### \- 🌐 \*\*Language-Aware\*\* — Detects resume language (English/Ukrainian) and adjusts tone + market.

##### \- 🔒 \*\*Access Control\*\* — Only approved users can use the bot (whitelist mode).

##### 

##### \## 🛠 Setup Instructions

##### 

##### \### 1. Clone the repository

##### ```bash

##### git clone https://github.com/your-username/cvise-bot.git

##### cd cvise-bot

##### 

##### 2\. Create .env file

##### TELEGRAM\_TOKEN=your\_telegram\_bot\_token

##### OPENAI\_API\_KEY=your\_openai\_api\_key

##### 

##### 3\. Install dependencies

##### pip install -r requirements.txt

##### 

##### 4\. Run the bot

##### python bot.py

##### 

##### ⚙️ Deployment

##### 

##### CVise works with long polling, but can be deployed to services like:

##### 

##### Render.com

##### 

##### Railway.app

##### 

##### Any VPS (Python + pip)

##### 

##### 📂 Project Structure

##### .

##### ├── bot.py                # Telegram bot logic \& routing

##### ├── analyzer.py           # Resume analysis and GPT prompts

##### ├── requirements.txt      # Dependencies

##### ├── .env                  # Secrets (excluded from Git)

##### └── README.md             # Documentation

##### 

##### 🧠 Powered by

##### 

##### GPT-4o via OpenAI API

##### 

##### Telegram Bot API

##### 

##### PyMuPDF \& python-docx

##### 

##### 📧 Contact

##### 

##### If you wish to access the bot, email: **mchprojects1@gmail.com**

