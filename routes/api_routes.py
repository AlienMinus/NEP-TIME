from flask import Blueprint, request, jsonify, session
from bson import ObjectId
from database import get_courses_col, get_users_col, serialize_doc
from services.auth_service import login_required
from services.course_service import (
    save_teacher_competencies,
    save_student_enrollment,
    assign_faculty_to_course,
    get_all_courses
)
from services.attendance_service import get_student_attendance_summary

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/courses", methods=["GET"])
@login_required()
def list_courses():
    courses = get_all_courses()
    return jsonify(serialize_doc(courses))

@api_bp.route("/teacher/competencies", methods=["POST"])
@login_required("teacher")
def save_competencies():
    uid = session.get("user_id")
    data = request.get_json(force=True, silent=True) or {}
    codes = data.get("subject_codes", [])
    success, msg = save_teacher_competencies(uid, codes)
    return jsonify({"success": success, "message": msg})

@api_bp.route("/student/enroll", methods=["POST"])
@login_required("student")
def enroll_courses():
    uid = session.get("user_id")
    data = request.get_json(force=True, silent=True) or {}
    theory_ids = data.get("theory_courses", [])
    lab_ids = data.get("lab_courses", [])
    success, msg = save_student_enrollment(uid, theory_ids, lab_ids)
    return jsonify({"success": success, "message": msg}), (200 if success else 400)

@api_bp.route("/admin/assign-faculty", methods=["POST"])
@login_required("admin")
def assign_faculty():
    data = request.get_json(force=True, silent=True) or {}
    course_id = data.get("course_id")
    teacher_id = data.get("teacher_id")

    if not course_id:
        return jsonify({"success": False, "message": "Missing course_id"}), 400

    success, msg = assign_faculty_to_course(course_id, teacher_id)
    return jsonify({"success": success, "message": msg})

@api_bp.route("/student/attendance", methods=["GET"])
@login_required("student")
def student_attendance_data():
    uid = session.get("user_id")
    summary = get_student_attendance_summary(uid)
    return jsonify(serialize_doc(summary))

