from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="WSBCO Golf Coach",
    version="0.3.0",
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Temporary storage.
# This will be replaced by Firestore later.
students: list[dict[str, str]] = []


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    navigation_cards = [
        {
            "title": "Students",
            "description": (
                "Manage player profiles, goals, contact information, "
                "lesson history, and progress."
            ),
            "icon": "students",
            "href": "/students",
            "status": "Available",
        },
        {
            "title": "Sessions",
            "description": (
                "Create lessons, review previous sessions, and connect "
                "launch data with coaching notes."
            ),
            "icon": "sessions",
            "href": "/sessions",
            "status": "Coming soon",
        },
        {
            "title": "Garmin Import",
            "description": (
                "Upload Garmin R10 CSV files, validate shot data, "
                "and assign shots to a coaching session."
            ),
            "icon": "import",
            "href": "/imports/garmin",
            "status": "Planned",
        },
        {
            "title": "Coaching Analysis",
            "description": (
                "Identify performance patterns, coaching priorities, "
                "recommended drills, and player development trends."
            ),
            "icon": "analysis",
            "href": "/analysis",
            "status": "Planned",
        },
    ]

    summary_cards = [
        {
            "label": "Students",
            "value": str(len(students)),
            "detail": "Active player profiles",
        },
        {
            "label": "Sessions",
            "value": "0",
            "detail": "Recorded coaching sessions",
        },
        {
            "label": "Shots",
            "value": "0",
            "detail": "Launch monitor shots",
        },
        {
            "label": "Analyses",
            "value": "0",
            "detail": "Completed coaching reviews",
        },
    ]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name": "WSBCO Golf Coach",
            "page_title": "Coach Dashboard",
            "version": app.version,
            "navigation_cards": navigation_cards,
            "summary_cards": summary_cards,
        },
    )


@app.get("/students", response_class=HTMLResponse)
async def student_list(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "app_name": "WSBCO Golf Coach",
            "page_title": "Students",
            "version": app.version,
            "students": students,
        },
    )


@app.post("/students")
async def create_student(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    skill_level: str = Form(""),
    primary_goal: str = Form(""),
):
    student = {
        "id": str(uuid4()),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "skill_level": skill_level.strip(),
        "primary_goal": primary_goal.strip(),
    }

    students.append(student)

    return RedirectResponse(
        url="/students",
        status_code=303,
    )


@app.post("/students/{student_id}/delete")
async def delete_student(student_id: str):
    global students

    students = [
        student
        for student in students
        if student["id"] != student_id
    ]

    return RedirectResponse(
        url="/students",
        status_code=303,
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "application": "WSBCO Golf Coach",
        "version": app.version,
        "students": len(students),
    }
