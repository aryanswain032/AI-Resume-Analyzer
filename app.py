from flask import Flask, render_template, request, redirect, url_for
import PyPDF2
import docx
import io
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    # This accepts ANY username/password for the demo
    return redirect(url_for('analyzer'))

@app.route('/analyzer')
def analyzer():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        resume_file = request.files['resume']
        job_desc = request.form['job_desc'].lower()
        
        if resume_file.filename == '':
            return render_template('index.html', error="Please select a file before clicking Analyze.")
            
        resume_text = ""
        
        if resume_file.filename.endswith('.pdf'):
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(resume_file.read()))
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text: resume_text += text + "\n"
            except Exception:
                return render_template('index.html', error="Could not read the PDF. It might be corrupted.")
                
        elif resume_file.filename.endswith('.docx'):
            try:
                doc = docx.Document(io.BytesIO(resume_file.read()))
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
            except Exception:
                return render_template('index.html', error="Could not read the Word document.")
        else:
            return render_template('index.html', error="Invalid file type. Please upload a PDF or DOCX file.")

        if len(resume_text.strip()) < 50:
            return render_template('index.html', error="The file appears to be empty or an image. Please upload a text-based PDF.")

        resume_text_lower = resume_text.lower()
        
        # --- FIX 1: SMART SYNONYM MATCHING (NLP GAP) ---
        # This replaces short forms in the resume so they match the JD
        synonyms = {"js": "javascript", "ml": "machine learning", "py": "python", "nlp": "natural language processing"}
        for short, full in synonyms.items():
            resume_text_lower = re.sub(r'\b' + short + r'\b', full, resume_text_lower)
            job_desc = re.sub(r'\b' + short + r'\b', full, job_desc)

        # --- REAL AI: SEMANTIC MATCHING (TF-IDF) ---
        documents = [resume_text_lower, job_desc]
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(documents)
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        semantic_score = int(cosine_sim * 100)

        # --- KEYWORD MATCHING ---
        skill_categories = {
            "Programming": ["python", "java", "javascript", "c++", "sql"],
            "Web Development": ["react", "html", "css", "flask", "django", "node.js"],
            "Data & AI": ["machine learning", "nlp", "data analysis", "pandas", "numpy"],
            "Tools & Cloud": ["github", "aws", "docker", "rest api"]
        }
        
        matched_skills = []
        missing_skills = []
        
        for category, skills in skill_categories.items():
            for skill in skills:
                if skill in job_desc:
                    if skill in resume_text_lower:
                        matched_skills.append(skill.upper())
                    else:
                        missing_skills.append(skill.upper())
                        
        total_required = len(matched_skills) + len(missing_skills)
        keyword_score = int((len(matched_skills) / total_required) * 100) if total_required > 0 else 0
        final_score = int((keyword_score * 0.6) + (semantic_score * 0.4))

        # --- ATS RESUME HEALTH SCORE ---
                # --- ATS RESUME HEALTH SCORE (STRICT) ---
                # --- ATS RESUME HEALTH SCORE (ULTRA STRICT) ---
        ats_score = 100
        ats_feedback = []
        
        # 1. Check Email
        has_email = "@" in resume_text
        if not has_email:
            ats_score -= 20
            
        # 2. Check Phone Number
        has_phone = bool(re.search(r'\d{10}', resume_text.replace("-", "").replace(" ", "")))
        if not has_phone:
            ats_score -= 20
            
        # 3. Check for Standard Resume Sections
        missing_sections = []
        if not re.search(r'(?i)(education|university|college|degree|b\.tech)', resume_text):
            ats_score -= 15
            missing_sections.append("Education")
        if not re.search(r'(?i)(experience|internship|worked|company|employment)', resume_text):
            ats_score -= 15
            missing_sections.append("Experience")
        if not re.search(r'(?i)(skills|technologies|tools|projects)', resume_text):
            ats_score -= 15
            missing_sections.append("Skills")
            
        if missing_sections:
            ats_feedback.append(f"Missing standard resume sections: {', '.join(missing_sections)}.")

        # 4. Check Length
        if len(resume_text.split()) < 150:
            ats_score -= 30
            ats_feedback.append("Document is too short. Add more details about your projects.")
            
        # 5. Check Dates (Years)
        if not re.search(r'(20\d{2}|19\d{2})', resume_text):
            ats_score -= 10
            ats_feedback.append("No dates (years) found. Use dates for your education and experience.")

        # --- THE KILL SWITCH (If it's not a resume, score is 0) ---
        # If there is no email AND no phone, OR if it's missing 2 or more core sections, it's not a resume.
        if (not has_email and not has_phone) or len(missing_sections) >= 2:
            ats_score = 0
            ats_feedback = ["🚨 ALERT: This document does NOT look like a standard resume. It is missing critical sections (Contact Info, Education, Experience). Please upload a proper resume."]
        elif ats_score < 0:
            ats_score = 0
        elif ats_score == 100:
            ats_feedback.append("Excellent! Your resume format passed all basic ATS checks.")

        # --- SMART SUGGESTIONS ---
        suggestions = []
        advice_db = {
            "REACT": "Build a simple React app (like a to-do list) and add it to your resume projects.",
            "SQL": "Practice basic database queries on platforms like HackerRank or LeetCode.",
            "AWS": "Try the AWS Cloud Practitioner free tier to learn cloud basics.",
            "MACHINE LEARNING": "Take a beginner course on Coursera or Kaggle to learn basic ML models.",
            "REST API": "Learn how to build a simple API using Python Flask or Node.js.",
            "GITHUB": "Create a free GitHub account and upload at least 2 of your coding projects."
        }

        for skill in missing_skills:
            if skill in advice_db:
                suggestions.append(f"To learn {skill}: {advice_db[skill]}")
            else:
                suggestions.append(f"Consider adding a small project using {skill} to your resume.")

        # --- FIX 2: JOB RECOMMENDATIONS (PPT GAP) ---
        recommended_jobs = []
        if "PYTHON" in matched_skills or "JAVASCRIPT" in matched_skills:
            recommended_jobs.append("Junior Software Developer")
        if "HTML" in matched_skills and "CSS" in matched_skills:
            recommended_jobs.append("Frontend Web Developer")
        if "MACHINE LEARNING" in matched_skills or "DATA ANALYSIS" in matched_skills:
            recommended_jobs.append("Data Analyst / ML Intern")
        if "SQL" in matched_skills and "PYTHON" in matched_skills:
            recommended_jobs.append("Backend Developer")
            
        if not recommended_jobs:
            recommended_jobs.append("Entry-Level IT Role (Based on current skills)")

        # --- EXTRACT EDUCATION & EXPERIENCE ---
        edu_match = re.search(r'(?i)(education|b\.tech|bachelor|master|degree|university|college)(.*?)(?=experience|skills|projects|$)', resume_text, re.DOTALL)
        education_info = edu_match.group(0).strip()[:200] + "..." if edu_match else "Education section not clearly detected."

        exp_match = re.search(r'(?i)(experience|internship|worked|employment|company)(.*?)(?=education|skills|projects|$)', resume_text, re.DOTALL)
        experience_info = exp_match.group(0).strip()[:200] + "..." if exp_match else "Experience section not clearly detected."

        return render_template('result.html', 
                               score=final_score, semantic_score=semantic_score,
                               ats_score=ats_score, ats_feedback=ats_feedback,
                               matched=matched_skills, missing=missing_skills, 
                               suggestions=suggestions, education=education_info, 
                               experience=experience_info, jobs=recommended_jobs)
    
    except Exception as e:
        return render_template('index.html', error="An unexpected error occurred. Please try again.")

@app.errorhandler(RequestEntityTooLarge)
def handle_file_size_error(e):
    return render_template('index.html', error="File is too large! Please upload a file smaller than 10MB."), 413

if __name__ == '__main__':
    app.run(debug=True)