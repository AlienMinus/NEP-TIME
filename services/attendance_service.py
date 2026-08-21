from datetime import datetime
from bson import ObjectId
from database import get_attendance_col, get_courses_col, get_users_col

def record_attendance(course_id_str, teacher_id_str, date_str, student_status_map):
    """
    Saves or updates subject-wise attendance for a list of students on a specific date.
    student_status_map: { "student_id_str": "present" | "absent" | "late" }
    """
    att_col = get_attendance_col()
    courses_col = get_courses_col()

    course = courses_col.find_one({"_id": ObjectId(course_id_str)})
    if not course:
        return False, "Course not found."

    course_name = f"{course.get('code', '')} {course.get('name', '')}".strip()

    saved_count = 0
    for sid_str, status in student_status_map.items():
        if not sid_str:
            continue
        try:
            sid = ObjectId(sid_str)
        except Exception:
            continue

        att_col.update_one(
            {
                "student_id": sid,
                "course_id": ObjectId(course_id_str),
                "date": date_str
            },
            {
                "$set": {
                    "status": status,
                    "course_name": course_name,
                    "teacher_id": ObjectId(teacher_id_str),
                    "student_group": course.get("student_group", ""),
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        saved_count += 1

    return True, f"Saved attendance for {saved_count} students on {date_str}."

def get_student_attendance_summary(student_id_str):
    """
    Returns aggregated stats and records for a student:
    - Subject-wise percentages
    - Overall attendance percentage
    - Low attendance warnings (< 75%)
    - Chart.js dataset
    """
    att_col = get_attendance_col()
    sid = ObjectId(student_id_str)

    rows = list(att_col.find({"student_id": sid}).sort("date", -1))
    
    subject_map = {}
    total_present = 0
    total_records = len(rows)

    for r in rows:
        cid = str(r["course_id"])
        cname = r.get("course_name", "Subject")
        status = r.get("status", "absent")

        if cid not in subject_map:
            subject_map[cid] = {
                "course_id": cid,
                "course_name": cname,
                "present": 0,
                "absent": 0,
                "late": 0,
                "total": 0
            }

        subject_map[cid]["total"] += 1
        if status == "present":
            subject_map[cid]["present"] += 1
            total_present += 1
        elif status == "late":
            subject_map[cid]["late"] += 1
            # Late counts as half or present for counting
            subject_map[cid]["present"] += 1
            total_present += 1
        else:
            subject_map[cid]["absent"] += 1

    stats_list = []
    chart_labels = []
    chart_values = []
    chart_colors = []

    for cid, data in subject_map.items():
        total = data["total"]
        pct = round((data["present"] / total) * 100, 1) if total > 0 else 0.0
        data["percent"] = pct
        data["is_low"] = pct < 75.0
        stats_list.append(data)

        chart_labels.append(data["course_name"])
        chart_values.append(pct)
        # Leaf Green if >= 75%, Orange/Red if < 75%
        chart_colors.append("#2e7d32" if pct >= 75.0 else "#e65100")

    overall_pct = round((total_present / total_records) * 100, 1) if total_records > 0 else 0.0

    return {
        "stats": stats_list,
        "rows": rows,
        "overall_percent": overall_pct,
        "total_records": total_records,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "chart_colors": chart_colors
    }

def get_admin_attendance_overview():
    """Returns college-wide attendance analytics for admin charts."""
    att_col = get_attendance_col()
    total_records = att_col.count_documents({})
    present_records = att_col.count_documents({"status": "present"})
    absent_records = att_col.count_documents({"status": "absent"})
    late_records = att_col.count_documents({"status": "late"})

    overall_rate = round((present_records / total_records) * 100, 1) if total_records > 0 else 0.0

    # Group by student_group
    group_stats = list(att_col.aggregate([
        {"$group": {
            "_id": "$student_group",
            "total": {"$sum": 1},
            "present": {
                "$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}
            }
        }}
    ]))

    for g in group_stats:
        g["rate"] = round((g["present"] / g["total"]) * 100, 1) if g["total"] > 0 else 0.0

    return {
        "total_records": total_records,
        "present_records": present_records,
        "absent_records": absent_records,
        "late_records": late_records,
        "overall_rate": overall_rate,
        "group_stats": group_stats
    }

