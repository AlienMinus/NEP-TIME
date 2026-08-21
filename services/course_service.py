from datetime import datetime
from bson import ObjectId
from database import get_courses_col, get_users_col, get_enrollments_col
from config import Config

MAX_THEORY = Config.MAX_THEORY_COURSES
MAX_LAB = Config.MAX_LAB_COURSES

def get_all_courses(query=None):
    col = get_courses_col()
    return list(col.find(query or {}).sort([("semester", 1), ("code", 1)]))

def get_course_by_id(course_id_str):
    try:
        return get_courses_col().find_one({"_id": ObjectId(course_id_str)})
    except Exception:
        return None

def create_or_update_course(data, course_id_str=None):
    col = get_courses_col()
    users_col = get_users_col()

    teacher_id = None
    teacher_name = "Unassigned"
    if data.get("teacher_id"):
        try:
            tid = ObjectId(data["teacher_id"])
            t = users_col.find_one({"_id": tid})
            if t:
                teacher_id = tid
                teacher_name = t.get("name", "Faculty")
        except Exception:
            pass

    doc = {
        "code": data.get("code", "").upper().strip(),
        "name": data.get("name", "").strip(),
        "type": data.get("type", "theory"), # "theory" or "lab"
        "lab_duration": int(data.get("lab_duration", 2)) if data.get("type") == "lab" else 1, # 2 or 3 periods
        "category": data.get("category", "Major"), # Major, Minor, Multidisciplinary, AEC, SEC, VAC
        "sessions_per_week": int(data.get("sessions_per_week", 1 if data.get("type") == "lab" else 3)),
        "semester": int(data.get("semester", 1)),
        "student_group": data.get("student_group", "ECE-6A").strip(),
        "syllabus": data.get("syllabus", "").strip(),
        "room_name": data.get("room_name", "").strip(),
        "teacher_id": teacher_id,
        "teacher_name": teacher_name,
        "updated_at": datetime.utcnow()
    }

    if course_id_str:
        col.update_one({"_id": ObjectId(course_id_str)}, {"$set": doc})
        return str(course_id_str)
    else:
        doc["created_at"] = datetime.utcnow()
        res = col.insert_one(doc)
        return str(res.inserted_id)

def delete_course(course_id_str):
    col = get_courses_col()
    col.delete_one({"_id": ObjectId(course_id_str)})
    return True

def assign_faculty_to_course(course_id_str, teacher_id_str):
    col = get_courses_col()
    users_col = get_users_col()

    teacher_id = None
    teacher_name = "Unassigned"
    if teacher_id_str:
        t = users_col.find_one({"_id": ObjectId(teacher_id_str)})
        if t:
            teacher_id = t["_id"]
            teacher_name = t.get("name", "Faculty")

    col.update_one(
        {"_id": ObjectId(course_id_str)},
        {"$set": {"teacher_id": teacher_id, "teacher_name": teacher_name, "updated_at": datetime.utcnow()}}
    )
    return True, f"Assigned {teacher_name} to course."

# --- Teacher Competency (Subject Bubbles) ---
def get_teacher_competencies(teacher_id_str):
    users_col = get_users_col()
    u = users_col.find_one({"_id": ObjectId(teacher_id_str)})
    return u.get("teaching_subjects", []) if u else []

def save_teacher_competencies(teacher_id_str, subject_codes):
    users_col = get_users_col()
    # Normalize list of codes
    clean_codes = list(set([c.strip().upper() for c in subject_codes if c.strip()]))
    users_col.update_one(
        {"_id": ObjectId(teacher_id_str)},
        {"$set": {"teaching_subjects": clean_codes, "updated_at": datetime.utcnow()}}
    )
    return True, "Teaching subject competencies updated."

# --- Student Course Selection (Max 6 Theory, Max 4 Lab) ---
def get_student_enrollments(student_id_str):
    enr_col = get_enrollments_col()
    rec = enr_col.find_one({"student_id": ObjectId(student_id_str)})
    if not rec:
        return {"theory_course_ids": [], "lab_course_ids": [], "updated_at": None}
    return {
        "theory_course_ids": [str(cid) for cid in rec.get("theory_course_ids", [])],
        "lab_course_ids": [str(cid) for cid in rec.get("lab_course_ids", [])],
        "updated_at": rec.get("updated_at")
    }

def save_student_enrollment(student_id_str, theory_ids, lab_ids):
    """
    Validates and saves student drag-and-drop course enrollment.
    Enforces MAX 6 Theory and MAX 4 Lab courses.
    """
    enr_col = get_enrollments_col()
    courses_col = get_courses_col()

    # Deduplicate
    theory_ids = list(set([tid for tid in theory_ids if tid]))
    lab_ids = list(set([lid for lid in lab_ids if lid]))

    if len(theory_ids) > MAX_THEORY:
        return False, f"Cannot select more than {MAX_THEORY} Theory courses (selected: {len(theory_ids)})."

    if len(lab_ids) > MAX_LAB:
        return False, f"Cannot select more than {MAX_LAB} Lab courses (selected: {len(lab_ids)})."

    # Validate that IDs correspond to correct course types
    valid_theory_oids = []
    for tid in theory_ids:
        try:
            c = courses_col.find_one({"_id": ObjectId(tid)})
            if c:
                valid_theory_oids.append(c["_id"])
        except Exception:
            continue

    valid_lab_oids = []
    for lid in lab_ids:
        try:
            c = courses_col.find_one({"_id": ObjectId(lid)})
            if c:
                valid_lab_oids.append(c["_id"])
        except Exception:
            continue

    enr_col.update_one(
        {"student_id": ObjectId(student_id_str)},
        {
            "$set": {
                "theory_course_ids": valid_theory_oids,
                "lab_course_ids": valid_lab_oids,
                "theory_count": len(valid_theory_oids),
                "lab_count": len(valid_lab_oids),
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    return True, f"Successfully enrolled in {len(valid_theory_oids)} Theory and {len(valid_lab_oids)} Lab courses."

