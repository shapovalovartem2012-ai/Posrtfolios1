import os
import uuid
import sqlite3
import requests
from flask import Flask, request, redirect, render_template, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

DB_PATH = "portfolios.db"
UPLOAD_DIR = os.path.join("static", "uploads")


def create_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        bio TEXT NOT NULL,
        github TEXT,
        telegram TEXT,
        avatar TEXT,
        skills TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def test_user():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO portfolios (uuid, name, bio, skills, avatar)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "123",
        "Данил Орлов",
        "Frontend-разработчик",
        "Python, HTML, Flask",
        "uploads/placeholder.png"
    ))
    conn.commit()
    conn.close()


@app.route("/")
def all_portfolios():
    tool_icons = {
        "Python": "🐍", "Flask": "🔧", "HTML": "📄", "CSS": "🎨",
        "HTML/CSS": "🖌️", "Git": "⛏️", "GitHub": "🧑‍💻", "Telegram": "✈️",
        "Телеграм": "✈️", "SQL": "📊", "SQLite": "🟪", "JavaScript": "📘",
        "JS": "⚡", "Jinja": "🛠️"
    }
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT uuid, name, avatar, bio, skills FROM portfolios")
    raw_data = cursor.fetchall()
    conn.close()

    filter_skill = request.args.get('skills')
    if filter_skill:
        filter_skill = filter_skill.strip().lower()
    else:
        filter_skill = None

    portfolios = []
    for uuid_, name, avatar, bio, skills_str in raw_data:
        skills = []
        for s in skills_str.split(','):
            s = s.strip()
            if s:
                skills.append(s)

        skills_lower = [s.lower() for s in skills]

        if filter_skill is None or filter_skill in skills_lower:
            portfolios.append((uuid_, name, avatar, bio, skills))

    return render_template(
        "all_portfolios.html",
        portfolios=portfolios,
        tool_icons=tool_icons,
        current_skills=filter_skill or ''
    )


@app.route("/form")
def form_page():
    return render_template("form.html")


@app.route("/generate", methods=["POST"])
def generate():
    form = request.form
    avatar = request.files.get("avatar")

    uid = str(uuid.uuid4())

    name = form.get("name", "").strip()
    bio = form.get("bio", "").strip()

    github = form.get("github", "").strip()
    github = github.replace("https://github.com/", "").replace("/", "")

    telegram = form.get("telegram", "").strip()
    skills = form.get("skills", "").strip()

    avatar_relpath = ""
    if avatar and avatar.filename:
        filename = secure_filename(f"{uid}_{avatar.filename}")
        save_path = os.path.join(UPLOAD_DIR, filename)
        avatar.save(save_path)
        avatar_relpath = os.path.join("uploads", filename).replace("\\", "/")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO portfolios (uuid, name, bio, github, telegram, avatar, skills)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (uid, name, bio, github, telegram, avatar_relpath, skills))
    conn.commit()
    conn.close()

    return redirect(url_for("all_portfolios"))


@app.route('/portfolio/<uuid>')
def view_portfolio(uuid):
    tool_icons = {
        "Python": "🐍", "Flask": "🔧", "HTML": "📄", "CSS": "🎨",
        "HTML/CSS": "🖌️", "Git": "⛏️", "GitHub": "🧑‍💻", "Telegram": "✈️",
        "Телеграм": "✈️", "SQL": "📊", "SQLite": "🟪", "JavaScript": "📘",
        "JS": "⚡", "Jinja": "🛠️"
    }
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, bio, github, telegram, avatar, skills
        FROM portfolios WHERE uuid = ?
    """, (uuid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Портфолио не найдено", 404

    skills = [s.strip() for s in row["skills"].split(",") if s.strip()]

    projects = []
    if row["github"]:
        try:
            url = f"https://api.github.com/users/{row['github']}/repos"
            response = requests.get(url, timeout=5)
            if response.ok:
                repos = response.json()[:6]
                for repo in repos:
                    projects.append({
                        "title": repo.get("name"),
                        "description": repo.get("description") or "Без описания",
                        "link": repo.get("html_url"),
                    })
        except Exception as e:
            print("Ошибка при запросе к GitHub:", e)

    return render_template(
        "portfolio_template.html",
        name=row["name"],
        bio=row["bio"],
        github=row["github"],
        telegram=row["telegram"],
        avatar=row["avatar"],
        skills=skills,
        projects=projects,
        tool_icons=tool_icons
    )


if __name__ == "__main__":
    create_db()
    test_user()
    app.run(debug=True)