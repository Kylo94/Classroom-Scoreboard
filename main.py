"""Classroom scoreboard - FastAPI app."""
import csv
import io
import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import database as db

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Classroom Scoreboard")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Ensure tables exist before handling any request. Idempotent thanks to
# IF NOT EXISTS, so it's safe to run on every import. This avoids the failure
# mode where the DB file gets recreated empty (e.g. user deletes it after
# startup) and the first request finds no tables.
db.init_db()


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    classes = db.list_classes()
    # Show the first class by default, if any.
    selected = classes[0] if classes else None
    students = db.list_students(selected["id"]) if selected else []
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "classes": classes,
            "selected_class": selected,
            "students": students,
        },
    )


@app.get("/class/{class_id}", response_class=HTMLResponse)
def class_page(request: Request, class_id: int):
    classes = db.list_classes()
    selected = next((c for c in classes if c["id"] == class_id), None)
    if selected is None:
        raise HTTPException(status_code=404, detail="Class not found")
    students = db.list_students(class_id)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "classes": classes,
            "selected_class": selected,
            "students": students,
        },
    )


# ---------- Class actions ----------

@app.post("/classes/create")
def create_class(name: str = Form(...)):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Class name is required")
    classes = db.list_classes()
    if any(c["name"] == name for c in classes):
        raise HTTPException(status_code=400, detail="Class already exists")
    new_id = db.create_class(name)
    return RedirectResponse(url=f"/class/{new_id}", status_code=303)


@app.post("/classes/{class_id}/delete")
def delete_class(class_id: int):
    db.delete_class(class_id)
    classes = db.list_classes()
    target = f"/class/{classes[0]['id']}" if classes else "/"
    return RedirectResponse(url=target, status_code=303)


@app.post("/classes/{class_id}/reset")
def reset_class(class_id: int):
    db.reset_class_scores(class_id)
    return RedirectResponse(url=f"/class/{class_id}", status_code=303)


# ---------- Student actions ----------

@app.post("/classes/{class_id}/students/add")
def add_student(class_id: int, name: str = Form(...)):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Student name is required")
    db.add_student(class_id, name)
    return RedirectResponse(url=f"/class/{class_id}", status_code=303)


@app.post("/classes/{class_id}/students/{student_id}/delete")
def remove_student(class_id: int, student_id: int):
    db.delete_student(student_id)
    return RedirectResponse(url=f"/class/{class_id}", status_code=303)


@app.post("/classes/{class_id}/students/{student_id}/rename")
def rename_student(class_id: int, student_id: int, name: str = Form(...)):
    ok = db.rename_student(student_id, name)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or duplicate name")
    return {"student_id": student_id, "name": name.strip()}


@app.post("/classes/{class_id}/students/{student_id}/score")
def update_score(class_id: int, student_id: int, delta: int = Form(...)):
    new_score = db.adjust_score(student_id, delta)
    if new_score is None:
        raise HTTPException(status_code=404, detail="Student not found")
    # Return JSON for the small JS handler to update the UI in place.
    return {"student_id": student_id, "score": new_score}


# ---------- Admin / export ----------

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    summaries = db.class_summary()
    # Nest students into each summary row so the template can render details.
    classes = []
    total_students = 0
    grand_score = 0
    for s in summaries:
        students = db.list_students(s["id"])
        total_students += len(students)
        grand_score += s["total_score"]
        classes.append({**dict(s), "students": students})
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "classes": classes,
            "total_classes": len(classes),
            "total_students": total_students,
            "grand_score": grand_score,
        },
    )


@app.get("/admin/export/json")
def export_json():
    payload = db.export_snapshot()
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="scoreboard.json"'
        },
    )


@app.get("/admin/export/csv")
def export_csv():
    classes = db.class_summary()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["class", "student", "score"])
    for c in classes:
        for s in db.list_students(c["id"]):
            writer.writerow([c["name"], s["name"], s["score"]])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="scoreboard.csv"'
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Bind to 0.0.0.0 so the app is reachable from the LAN (e.g. teacher's
    # tablet or projector at http://192.168.x.x:8000). Override with
    # SCOREBOARD_HOST / SCOREBOARD_PORT env vars if needed.
    import os
    host = os.environ.get("SCOREBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("SCOREBOARD_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)