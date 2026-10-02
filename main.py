import os
import json
import re
import time
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "edugenie_secret_key_123")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash"
]

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def generate_with_fallback(contents):
    last_error = None
    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                time.sleep(1)
                continue
    raise last_error

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check_session", methods=["GET"])
def check_session():
    if "user_id" in session:
        return jsonify({"logged_in": True, "username": session.get("username")})
    return jsonify({"logged_in": False})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("home"))

    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):
        session["user_id"] = user[0]
        session["username"] = user[1]
        return jsonify({"success": True, "username": user[1]})
    else:
        return jsonify({"error": "Invalid email or password"}), 401

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    hashed_pw = generate_password_hash(password)

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email or Username already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    if request.method == "GET":
        return redirect(url_for("home"))
    return jsonify({"success": True})

@app.route("/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    system_prompt = (
        "You are EduGenie, an expert AI tutor for computer science, AI & DS, and engineering students. "
        "Recognize syllabus context (e.g., Anna University Regulation 2021) if subject codes are provided. "
        "Explain the following concept thoroughly with clear definitions, bullet points, and key takeaways.\n\n"
        "MERMAID DIAGRAM RULES:\n"
        "- If drawing a diagram, use ONLY valid and simple Mermaid syntax inside ```mermaid code blocks.\n"
        "- Always start with 'flowchart TD' or 'graph TD'.\n"
        "- NEVER use special characters like parenthesis (), brackets [], or colons : inside node text unless strictly enclosed in double quotes (e.g. A[\"Confidentiality\"]).\n"
        "- Keep node IDs simple like A, B, C, D.\n\n"
        f"{prompt}"
    )

    try:
        reply_text = generate_with_fallback(system_prompt)
        return jsonify({"reply": reply_text, "topic": prompt})
    except Exception as e:
        return jsonify({"error": f"Model busy. Please try again: {str(e)}"}), 503

@app.route("/quiz", methods=["POST"])
def quiz():
    if "user_id" not in session:
        return jsonify({"error": "Please login first"}), 401

    data = request.get_json() or {}
    topic = data.get("topic", "").strip()
    level = data.get("level", "Understanding")

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    quiz_prompt = f"""
    You are an expert engineering examiner. Generate a 3-question MCQ quiz for topic '{topic}' aligned with Bloom's Taxonomy level: '{level}'.
    Return strictly a valid JSON array of objects without Markdown formatting or backticks.
    Each object must have exactly these keys:
    - "question": "The question string"
    - "options": ["Option A", "Option B", "Option C", "Option D"]
    - "answer_index": 0 (Integer: 0 for Option A, 1 for B, 2 for C, 3 for D)
    - "explanation": "Short 1-line explanation"
    """

    try:
        raw_text = generate_with_fallback(quiz_prompt)
        cleaned_json = re.sub(r"^```json|^```|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        quiz_data = json.loads(cleaned_json)
        return jsonify({"quiz": quiz_data})
    except Exception as e:
        return jsonify({"error": f"Failed to generate structured quiz: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)