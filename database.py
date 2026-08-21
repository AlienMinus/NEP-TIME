import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from config import Config

client = None
db = None

def init_db(app=None):
    global client, db
    mongo_uri = os.getenv("MONGO_URI", Config.MONGO_URI)
    db_name = os.getenv("MONGO_DB", Config.MONGO_DB)
    if mongo_uri:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        create_indexes()
    return db

def get_db():
    global db
    if db is None:
        init_db()
    return db

def get_users_col():
    return get_db().users

def get_courses_col():
    return get_db().courses

def get_timetable_col():
    return get_db().timetable

def get_attendance_col():
    return get_db().attendance

def get_otps_col():
    return get_db().otps

def get_enrollments_col():
    return get_db().student_enrollments

def create_indexes():
    """Ensure fast lookups and unique constraints where needed."""
    try:
        get_users_col().create_index("email", unique=True)
        get_users_col().create_index("role")
        get_users_col().create_index("student_group")
        get_courses_col().create_index([("code", ASCENDING), ("student_group", ASCENDING)])
        get_timetable_col().create_index([("student_group", ASCENDING), ("day_index", ASCENDING), ("period", ASCENDING)])
        get_timetable_col().create_index([("teacher_id", ASCENDING), ("day_index", ASCENDING), ("period", ASCENDING)])
        get_attendance_col().create_index([("course_id", ASCENDING), ("student_id", ASCENDING), ("date", ASCENDING)])
        get_enrollments_col().create_index("student_id", unique=True)
        get_otps_col().create_index("expires", expireAfterSeconds=0)
    except Exception as e:
        print(f"[DB INDEX WARNING] {e}")

def serialize_doc(doc):
    """Recursively convert BSON ObjectIds to string for JSON output."""
    if not doc:
        return doc
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, list):
                result[k] = [serialize_doc(i) for i in v]
            elif isinstance(v, dict):
                result[k] = serialize_doc(v)
            else:
                result[k] = v
        return result
    return doc

