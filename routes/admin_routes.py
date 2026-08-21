from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from bson import ObjectId
from database import get_users_col, get_courses_col, get_timetable_col, get_attendance_col
from services.auth_service import login_required
from services.timetable_service import generate_conflict_free_timetable, DAYS, PERIODS_YEAR_1, PERIODS_OTHER_YEARS
from services.course_service import (
    get_all_courses,
    get_course_by_id,
    create_or_update_course,
    delete_course,
    assign_faculty_to_course
)
from services.attendance_service import get_admin_attendance_overview
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@login_required("admin")
def dashboard():
    users_col = get_users_col()
    courses_col = get_courses_col()
    tt_col = get_timetable_col()
    att_col = get_attendance_col()

    stats = {
        "students": users_col.count_documents({"role": "student"}),
        "teachers": users_col.count_documents({"role": "teacher"}),
        "courses": courses_col.count_documents({}),
        "timetable_entries": tt_col.count_documents({}),
        "attendance_records": att_col.count_documents({})
    }

    # Chart datasets
    role_data = list(users_col.aggregate([{"$group": {"_id": "$role", "count": {"$sum": 1}}}]))
    category_data = list(courses_col.aggregate([{"$group": {"_id": "$category", "count": {"$sum": 1}}}]))
    type_data = list(courses_col.aggregate([{"$group": {"_id": "$type", "count": {"$sum": 1}}}]))
    dept_data = list(users_col.aggregate([
        {"$match": {"role": "student"}},
        {"$group": {"_id": "$program", "count": {"$sum": 1}}}
    ]))

    att_overview = get_admin_attendance_overview()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        role_data=role_data,
        category_data=category_data,
        type_data=type_data,
        dept_data=dept_data,
        att_overview=att_overview
    )

@admin_bp.route("/subjects", methods=["GET", "POST"])
@login_required("admin")
def subjects():
    courses_col = get_courses_col()
    users_col = get_users_col()

    if request.method == "POST":
        data = {
            "code": request.form.get("code"),
            "name": request.form.get("name"),
            "type": request.form.get("type", "theory"),
            "lab_duration": int(request.form.get("lab_duration", 2)),
            "category": request.form.get("category", "Major"),
            "sessions_per_week": int(request.form.get("sessions_per_week", 3)),
            "semester": int(request.form.get("semester", 1)),
            "student_group": request.form.get("student_group", "ECE-6A"),
            "teacher_id": request.form.get("teacher_id", ""),
            "syllabus": request.form.get("syllabus", ""),
            "room_name": request.form.get("room_name", "")
        }
        create_or_update_course(data)
        flash(f"Subject {data['code']} added successfully.", "success")
        return redirect(url_for("admin.subjects"))

    courses = get_all_courses()
    teachers = list(users_col.find({"role": "teacher"}).sort("name", 1))
    student_groups = list(users_col.distinct("student_group", {"role": "student"}))

    return render_template(
        "admin/subjects.html",
        courses=courses,
        teachers=teachers,
        student_groups=student_groups
    )

@admin_bp.route("/subjects/<course_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def edit_subject(course_id):
    users_col = get_users_col()
    course = get_course_by_id(course_id)
    if not course:
        flash("Subject not found.", "danger")
        return redirect(url_for("admin.subjects"))

    if request.method == "POST":
        data = {
            "code": request.form.get("code"),
            "name": request.form.get("name"),
            "type": request.form.get("type", "theory"),
            "lab_duration": int(request.form.get("lab_duration", 2)),
            "category": request.form.get("category", "Major"),
            "sessions_per_week": int(request.form.get("sessions_per_week", 3)),
            "semester": int(request.form.get("semester", 1)),
            "student_group": request.form.get("student_group", "ECE-6A"),
            "teacher_id": request.form.get("teacher_id", ""),
            "syllabus": request.form.get("syllabus", ""),
            "room_name": request.form.get("room_name", "")
        }
        create_or_update_course(data, course_id)
        flash(f"Subject {data['code']} updated successfully.", "success")
        return redirect(url_for("admin.subjects"))

    teachers = list(users_col.find({"role": "teacher"}).sort("name", 1))
    return render_template("admin/subject_edit.html", course=course, teachers=teachers)

@admin_bp.route("/subjects/<course_id>/delete", methods=["POST"])
@login_required("admin")
def delete_subject_route(course_id):
    delete_course(course_id)
    flash("Subject deleted successfully.", "info")
    return redirect(url_for("admin.subjects"))

@admin_bp.route("/faculty-assign", methods=["GET", "POST"])
@login_required("admin")
def faculty_assign():
    courses_col = get_courses_col()
    users_col = get_users_col()

    courses = list(courses_col.find({}).sort([("semester", 1), ("student_group", 1), ("code", 1)]))
    teachers = list(users_col.find({"role": "teacher"}).sort("name", 1))
    student_groups = sorted(list(set(c.get("student_group", "General") for c in courses if c.get("student_group"))))

    return render_template(
        "admin/faculty_assign.html",
        courses=courses,
        teachers=teachers,
        student_groups=student_groups
    )

@admin_bp.route("/timetable", methods=["GET"])
@login_required("admin")
def timetable_view():
    tt_col = get_timetable_col()
    courses_col = get_courses_col()

    groups = sorted(list(set(c.get("student_group", "ECE-6A") for c in courses_col.find({}) if c.get("student_group"))))
    selected_group = request.args.get("group", groups[0] if groups else "ECE-6A")

    entries = list(tt_col.find({"student_group": selected_group}).sort([("day_index", 1), ("period", 1)]))

    # Grid mapping
    grid = {}
    for e in entries:
        grid[(e["day_index"], e["period"])] = e

    return render_template(
        "admin/timetable.html",
        groups=groups,
        selected_group=selected_group,
        grid=grid,
        days=DAYS,
        entries_count=len(entries)
    )

@admin_bp.route("/timetable/generate", methods=["POST"])
@login_required("admin")
def timetable_generate():
    group_filter = request.form.get("student_group") or None
    success, msg = generate_conflict_free_timetable(group_filter=group_filter)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "warning")
    return redirect(url_for("admin.timetable_view", group=group_filter if group_filter else ""))

@admin_bp.route("/timetable/clear", methods=["POST"])
@login_required("admin")
def timetable_clear():
    tt_col = get_timetable_col()
    group_filter = request.form.get("student_group")
    if group_filter:
        tt_col.delete_many({"student_group": group_filter})
        flash(f"Timetable cleared for group {group_filter}.", "info")
    else:
        tt_col.delete_many({})
        flash("All timetable entries cleared.", "info")
    return redirect(url_for("admin.timetable_view"))

