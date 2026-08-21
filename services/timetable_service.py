from bson import ObjectId
from database import get_timetable_col, get_courses_col, get_users_col
from config import Config

DAYS = Config.DAYS
PERIODS_YEAR_1 = Config.PERIODS_YEAR_1
PERIODS_OTHER_YEARS = Config.PERIODS_OTHER_YEARS
LUNCH_YEAR_1 = Config.LUNCH_YEAR_1
LUNCH_OTHER_YEARS = Config.LUNCH_OTHER_YEARS

def get_periods_for_year(year_or_sem):
    """Return period list and lunch break based on semester or year."""
    try:
        sem = int(year_or_sem)
    except (ValueError, TypeError):
        sem = 3
    
    if sem in [1, 2]:
        return PERIODS_YEAR_1, LUNCH_YEAR_1
    return PERIODS_OTHER_YEARS, LUNCH_OTHER_YEARS

def get_valid_lab_start_periods(duration_periods: int, is_first_year: bool) -> list[int]:
    """
    Return list of starting period numbers (1-indexed) where a lab of duration_periods
    can fit without crossing the lunch break.
    """
    if is_first_year:
        # Periods before lunch: 1, 2 (Lunch: 10:05-10:35)
        # Periods after lunch: 3, 4, 5, 6
        if duration_periods == 2:
            return [1, 3, 4, 5]
        elif duration_periods == 3:
            return [3, 4]
        else:
            return [1, 3, 4, 5]
    else:
        # Periods before lunch: 1, 2, 3 (Lunch: 11:00-11:30)
        # Periods after lunch: 4, 5, 6
        if duration_periods == 2:
            return [1, 2, 4, 5]
        elif duration_periods == 3:
            return [1, 4]
        else:
            return [1, 2, 4, 5]

def generate_conflict_free_timetable(group_filter=None):
    """
    Automatic intelligent timetable generator for ABIT.
    Ensures ZERO conflicts across:
    1. Faculty schedules
    2. Student Group schedules
    3. Room / Lab allocations
    4. Respects 1st year vs other years lunch breaks
    5. Allocates contiguous 2-hour / 3-hour lab sessions
    """
    courses_col = get_courses_col()
    users_col = get_users_col()
    tt_col = get_timetable_col()

    query = {}
    if group_filter:
        query["student_group"] = group_filter

    course_list = list(courses_col.find(query))
    if not course_list:
        return False, "No courses found to schedule."

    # Fetch teachers map
    teachers = {str(u["_id"]): u.get("name", "Faculty") for u in users_col.find({"role": "teacher"})}

    # Data structures for conflict tracking:
    # teacher_occupied: (teacher_id_str, day_idx, period_num) -> course_info
    # group_occupied: (group_str, day_idx, period_num) -> course_info
    # room_occupied: (room_str, day_idx, period_num) -> course_info
    teacher_occupied = {}
    group_occupied = {}
    room_occupied = {}

    # If generating for a specific group, preserve other groups' schedule
    if group_filter:
        existing = list(tt_col.find({"student_group": {"$ne": group_filter}}))
        for item in existing:
            d = item["day_index"]
            p = item["period"]
            if item.get("teacher_id"):
                teacher_occupied[(str(item["teacher_id"]), d, p)] = item
            if item.get("student_group"):
                group_occupied[(item["student_group"], d, p)] = item
            if item.get("room_name"):
                room_occupied[(item["room_name"], d, p)] = item

    # Sort courses: Labs first (highest constraint), then high sessions per week
    def course_sort_key(c):
        is_lab = 1 if c.get("type") == "lab" else 0
        dur = int(c.get("lab_duration", 2)) if is_lab else 1
        sessions = int(c.get("sessions_per_week", 3))
        return (is_lab, dur, sessions)

    sorted_courses = sorted(course_list, key=course_sort_key, reverse=True)

    new_timetable_entries = []

    # Helper to check if a block of slots is free
    def can_place(c, day, start_p, duration):
        group = c.get("student_group", "")
        tid = str(c.get("teacher_id", "")) if c.get("teacher_id") else ""
        room = c.get("room_name", "") or ("Lab-" + c.get("code", "01") if c.get("type") == "lab" else "LH-" + group)

        for p in range(start_p, start_p + duration):
            if p > 6:
                return False
            if (group, day, p) in group_occupied:
                return False
            if tid and (tid, day, p) in teacher_occupied:
                return False
            if room and (room, day, p) in room_occupied:
                return False
        return True

    def place_course_block(c, day, start_p, duration):
        group = c.get("student_group", "")
        tid = c.get("teacher_id")
        tid_str = str(tid) if tid else ""
        tname = teachers.get(tid_str, c.get("teacher_name", "Faculty"))
        room = c.get("room_name", "") or ("Lab-" + c.get("code", "01") if c.get("type") == "lab" else "Room-" + group)
        sem = int(c.get("semester", 1))
        is_yr1 = sem in [1, 2]
        periods_def, _ = get_periods_for_year(sem)

        for p in range(start_p, start_p + duration):
            period_meta = next((x for x in periods_def if x["period"] == p), {"start": "", "end": ""})
            entry = {
                "course_id": c["_id"],
                "code": c["code"],
                "name": c["name"],
                "type": c.get("type", "theory"),
                "category": c.get("category", "Major"),
                "semester": sem,
                "student_group": group,
                "teacher_id": tid,
                "teacher_name": tname,
                "room_name": room,
                "day_index": day,
                "day_name": DAYS[day],
                "period": p,
                "start_time": period_meta.get("start", ""),
                "end_time": period_meta.get("end", ""),
                "duration_blocks": duration,
                "is_lab_block": duration > 1,
                "block_start_period": start_p
            }
            new_timetable_entries.append(entry)
            group_occupied[(group, day, p)] = entry
            if tid_str:
                teacher_occupied[(tid_str, day, p)] = entry
            if room:
                room_occupied[(room, day, p)] = entry

    # Schedule each course
    unplaced_warnings = []
    for c in sorted_courses:
        sem = int(c.get("semester", 1))
        is_yr1 = sem in [1, 2]
        is_lab = (c.get("type") == "lab")
        dur = int(c.get("lab_duration", 2)) if is_lab else 1
        sessions_needed = int(c.get("sessions_per_week", 1 if is_lab else 3))

        valid_starts = get_valid_lab_start_periods(dur, is_yr1) if is_lab else [1, 2, 3, 4, 5, 6]

        sessions_placed = 0
        days_order = list(range(6))
        # Stagger days to avoid clustering
        if not is_lab:
            # Spread days like [0, 2, 4, 1, 3, 5]
            days_order = [0, 2, 4, 1, 3, 5]

        for d in days_order:
            if sessions_placed >= sessions_needed:
                break
            placed_for_day = False
            for sp in valid_starts:
                if can_place(c, d, sp, dur):
                    place_course_block(c, d, sp, dur)
                    sessions_placed += 1
                    placed_for_day = True
                    break
            if not placed_for_day and is_lab:
                # Try fallback starts
                for sp in range(1, 7 - dur + 1):
                    if sp in valid_starts and can_place(c, d, sp, dur):
                        place_course_block(c, d, sp, dur)
                        sessions_placed += 1
                        break

        if sessions_placed < sessions_needed:
            unplaced_warnings.append(f"Course {c.get('code')} ({c.get('name')}): placed {sessions_placed}/{sessions_needed} sessions.")

    # Save to MongoDB
    if group_filter:
        tt_col.delete_many({"student_group": group_filter})
    else:
        tt_col.delete_many({})

    if new_timetable_entries:
        tt_col.insert_many(new_timetable_entries)

    msg = f"Generated conflict-free timetable ({len(new_timetable_entries)} periods scheduled)."
    if unplaced_warnings:
        msg += " Note: " + "; ".join(unplaced_warnings)
    return True, msg

def get_teacher_schedule_with_leisure(teacher_id_str):
    """
    Fetches teacher schedule and highlights leisure / free periods across Monday-Saturday (Periods 1-6).
    """
    tt_col = get_timetable_col()
    entries = list(tt_col.find({"teacher_id": ObjectId(teacher_id_str)}))

    # Map by (day_index, period)
    schedule_grid = {}
    for item in entries:
        d = item["day_index"]
        p = item["period"]
        schedule_grid[(d, p)] = item

    # Build full weekly 6x6 matrix with Leisure periods identified
    weekly_matrix = []
    total_classes = len(entries)
    total_leisure = 36 - total_classes

    for day_idx, day_name in enumerate(DAYS):
        day_slots = []
        for p in range(1, 7):
            # Periods config defaults to standard
            p_meta = next((x for x in PERIODS_OTHER_YEARS if x["period"] == p), {})
            if (day_idx, p) in schedule_grid:
                entry = schedule_grid[(day_idx, p)]
                day_slots.append({
                    "period": p,
                    "is_leisure": False,
                    "course_name": entry.get("name"),
                    "course_code": entry.get("code"),
                    "type": entry.get("type"),
                    "student_group": entry.get("student_group"),
                    "room_name": entry.get("room_name"),
                    "start_time": entry.get("start_time", p_meta.get("start")),
                    "end_time": entry.get("end_time", p_meta.get("end")),
                    "is_lab": entry.get("is_lab_block", False)
                })
            else:
                day_slots.append({
                    "period": p,
                    "is_leisure": True,
                    "start_time": p_meta.get("start", ""),
                    "end_time": p_meta.get("end", ""),
                    "label": "Leisure / Free Period"
                })
        weekly_matrix.append({
            "day_index": day_idx,
            "day_name": day_name,
            "slots": day_slots
        })

    return {
        "weekly_matrix": weekly_matrix,
        "total_classes": total_classes,
        "total_leisure": total_leisure,
        "entries": entries
    }

def get_student_timetable(student_group, semester=1):
    """
    Fetches full student timetable for their group, applying year-specific periods and lunch break.
    """
    tt_col = get_timetable_col()
    entries = list(tt_col.find({"student_group": student_group}).sort([("day_index", 1), ("period", 1)]))

    periods_def, lunch_def = get_periods_for_year(semester)

    # Build weekly grid
    grid = {}
    for e in entries:
        grid[(e["day_index"], e["period"])] = e

    weekly_matrix = []
    for day_idx, day_name in enumerate(DAYS):
        slots = []
        for p_def in periods_def:
            p = p_def["period"]
            if (day_idx, p) in grid:
                item = grid[(day_idx, p)]
                slots.append({
                    "period": p,
                    "time": f"{p_def['start']} – {p_def['end']}",
                    "has_class": True,
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "type": item.get("type", "theory"),
                    "teacher": item.get("teacher_name", "—"),
                    "room": item.get("room_name", "—"),
                    "category": item.get("category", "Major")
                })
            else:
                slots.append({
                    "period": p,
                    "time": f"{p_def['start']} – {p_def['end']}",
                    "has_class": False,
                    "label": "Free / Self-Study"
                })
        weekly_matrix.append({
            "day_index": day_idx,
            "day_name": day_name,
            "slots": slots
        })

    return {
        "weekly_matrix": weekly_matrix,
        "lunch": lunch_def,
        "periods": periods_def,
        "entries": entries
    }

