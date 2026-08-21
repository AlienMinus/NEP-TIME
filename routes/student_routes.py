from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from database import get_users_col, get_courses_col
from services.auth_service import login_required
from services.timetable_service import get_student_timetable, DAYS
from services.attendance_service import get_student_attendance_summary
from services.course_service import (
    get_student_enrollments,
    save_student_enrollment,
    get_all_courses
)
from config import Config

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.route("/")
@login_required("student")
def dashboard():
    uid = session["user_id"]
    users_col = get_users_col()
    student = users_col.find_one({"_id": ObjectId(uid)})
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.login"))

    group = student.get("student_group", "ECE-6A")
    semester = student.get("semester", 1)

    timetable_data = get_student_timetable(group, semester)
    att_summary = get_student_attendance_summary(uid)

    return render_template(
        "student/dashboard.html",
        student=student,
        timetable=timetable_data,
        days=DAYS,
        att_summary=att_summary
    )

@student_bp.route("/courses", methods=["GET", "POST"])
@login_required("student")
def course_selection():
    uid = session["user_id"]
    users_col = get_users_col()
    student = users_col.find_one({"_id": ObjectId(uid)})
    if not student:
        return redirect(url_for("auth.login"))

    sem = student.get("semester", 1)
    group = student.get("student_group", "")

    # Query relevant courses for student's group or semester
    query = {}
    if group:
        query = {"$or": [{"student_group": group}, {"semester": sem}]}

    available_courses = get_all_courses(query)
    if not available_courses:
        # Fallback to all courses
        available_courses = get_all_courses()

    enrollment = get_student_enrollments(uid)

    if request.method == "POST":
        theory_ids = request.form.getlist("theory_courses")
        lab_ids = request.form.getlist("lab_courses")

        success, msg = save_student_enrollment(uid, theory_ids, lab_ids)
        if success:
            flash(msg, "success")
        else:
            flash(msg, "danger")
        return redirect(url_for("student.course_selection"))

    return render_template(
        "student/course_select.html",
        student=student,
        available_courses=available_courses,
        enrolled_theory_ids=enrollment["theory_course_ids"],
        enrolled_lab_ids=enrollment["lab_course_ids"],
        max_theory=Config.MAX_THEORY_COURSES,
        max_lab=Config.MAX_LAB_COURSES
    )

@student_bp.route("/attendance")
@login_required("student")
def attendance_view():
    uid = session["user_id"]
    users_col = get_users_col()
    student = users_col.find_one({"_id": ObjectId(uid)})
    if not student:
        return redirect(url_for("auth.login"))

    att_summary = get_student_attendance_summary(uid)

    return render_template(
        "student/attendance.html",
        student=student,
        att_summary=att_summary
    )

