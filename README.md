# STACKIT

A StackOverflow-style Q&A platform built with Flask + SQLite. Users can ask questions, answer, @mention, vote, and get notifications. Admins can manage users, delete questions, and ban accounts.

## Live Demo
- Replit: <ADD YOUR PUBLIC URL HERE>

## Features
- Auth: sign up / login / logout
- Ask & answer questions
- @Mentions + notifications
- Voting (+1 / −1)
- Admin dashboard (manage users & questions)
- Markdown/Quill editor
- Image uploads

## Tech Stack
- Python (Flask, Flask-Login, SQLAlchemy, Jinja2)
- SQLite
- Bootstrap + custom CSS

---

## Run Locally

### Option A — Poetry (recommended)
```bash
# 1) clone
git clone https://github.com/Tousif18/stackit.git
cd stackit

# 2) install deps
pipx install poetry  # if you don't have Poetry
poetry install

# 3) run
poetry run python main.py
Option B — pip (if you insist)
bash
Copy code
# create & activate a venv, then:
pip install -r requirements.txt
python main.py
If using Option B, generate requirements.txt once via:
poetry export -f requirements.txt -o requirements.txt --without-hashes

Configuration
Create a .env file (not committed) for secrets:

ini
Copy code
FLASK_SECRET_KEY=change-me
DATABASE_URL=sqlite:///app.db
The app reads from environment variables; fallbacks exist for local dev.

Screenshots
Add 2–4 images or a short GIF here (ask, answer, admin ban, notifications).

Roadmap
Pagination & search

Tags & user profiles

Email / push notifications

Dockerfile & GitHub Actions

License
MIT

yaml
Copy code
