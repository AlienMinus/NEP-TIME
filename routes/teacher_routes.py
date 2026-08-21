from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from database import get_users_col, get_courses_col, get_attendance_col
from services.auth_service import login_required
from services.timetable_service import get_teacher_schedule_with_leisure, DAYS
from services.course_service import get_teacher_competencies, save_teacher_competencies, get_all_courses
from services.attendance_service import record_attendance

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")

@teacher_bp.route("/")
@login_required("teacher")
def dashboard():
    uid = session["user_id"]
    users_col = get_users_col()
    courses_col = get_courses_col()

    teacher = users_col.find_one({"_id": ObjectId(uid)})
    if not teacher:
        flash("Teacher profile not found.", "danger")
        return redirect(url_for("auth.login"))

    # Assigned courses
    assigned_courses = list(courses_col.find({"teacher_id": ObjectId(uid)}).sort("code", 1))

    # Weekly schedule with leisure periods
    schedule_data = get_teacher_schedule_with_leisure(uid)

    # Subject competency bubbles
    all_courses = get_all_courses()
    all_subjects_pool = []
    seen = set()
    for c in all_courses:
        code = c.get("code")
        if code and code not in seen:
            seen.add(code)
            all_subjects_pool.append({
                "code": code,
                "name": c.get("name"),
                "type": c.get("type", "theory"),
                "category": c.get("category", "Major")
            })

    my_competencies = teacher.get("teaching_subjects", [])

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        assigned_courses=assigned_courses,
        schedule=schedule_data,
        days=DAYS,
        all_subjects_pool=all_subjects_pool,
        my_competencies=my_competencies
    )

@teacher_bp.route("/attendance/<course_id>", methods=["GET", "POST"])
@login_required("teacher")
def mark_attendance(course_id):
    uid = session["user_id"]
    courses_col = get_courses_col()
    users_col = get_users_col()
    att_col = get_attendance_col()

    course = courses_col.find_one({"_id": ObjectId(course_id), "teacher_id": ObjectId(uid)})
    if not course:
        # Fallback check if admin or if teacher assigned
        course = courses_col.find_one({"_id": ObjectId(course_id)})
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("teacher.dashboard"))

    target_group = course.get("student_group", "")
    students = list(users_col.find({"role": "student", "student_group": target_group}).sort("name", 1))

    selected_date = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    if request.method == "POST":
        selected_date = request.form.get("date", selected_date)
        status_map = {}
        for s in students:
            sid_str = str(s["_id"])
            status_map[sid_str] = request.form.get(f"student_{sid_str}", "absent")

        success, msg = record_attendance(course_id, uid, selected_date, status_map)
        if success:
            flash(msg, "success")
        else:
            flash(msg, "danger")
        return redirect(url_for("teacher.mark_attendance", course_id=course_id, date=selected_date))

    # Fetch existing records for this date to pre-populate
    existing_records = list(att_col.find({
        "course_id": ObjectId(course_id),
        "date": selected_date
    }))
    existing_status_map = {str(r["student_id"]): r.get("status", "present") for r in existing_records}

    return render_template(
        "teacher/attendance_mark.html",
        course=course,
        students=students,
        date=selected_date,
        existing_status_map=existing_status_map
    )

