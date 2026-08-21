import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "nep-time-abit-secret-key-2026")
    MONGO_URI = os.getenv("MONGO_URI", "")
    MONGO_DB = os.getenv("MONGO_DB", "neptime")

    # Cloudinary Config
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

    # EmailJS Config
    EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "")
    EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "")
    EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY", "")
    EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8080/auth/google/callback")

    # College Information
    COLLEGE_NAME = "Ajay Binay Institute of Technology (ABIT)"
    COLLEGE_SHORT = "ABIT"

    # Working Days
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    # ABIT Daily Timing: 08:15 AM to 02:15 PM (6 Lessons @ 55 mins each)
    # 1st Year Schedule (Semesters 1-2):
    #   Period 1: 08:15 - 09:10
    #   Period 2: 09:10 - 10:05
    #   Lunch Break (1st Year): 10:05 - 10:35 (30 mins)
    #   Period 3: 10:35 - 11:30
    #   Period 4: 11:30 - 12:25
    #   Period 5: 12:25 - 13:20
    #   Period 6: 13:20 - 14:15
    PERIODS_YEAR_1 = [
        {"period": 1, "start": "08:15", "end": "09:10", "label": "08:15 – 09:10"},
        {"period": 2, "start": "09:10", "end": "10:05", "label": "09:10 – 10:05"},
        {"period": 3, "start": "10:35", "end": "11:30", "label": "10:35 – 11:30"},
        {"period": 4, "start": "11:30", "end": "12:25", "label": "11:30 – 12:25"},
        {"period": 5, "start": "12:25", "end": "13:20", "label": "12:25 – 13:20"},
        {"period": 6, "start": "13:20", "end": "14:15", "label": "13:20 – 14:15"},
    ]
    LUNCH_YEAR_1 = {"start": "10:05", "end": "10:35", "label": "10:05 – 10:35 AM"}

    # Other Years Schedule (2nd, 3rd, 4th Year / Semesters 3-8):
    #   Period 1: 08:15 - 09:10
    #   Period 2: 09:10 - 10:05
    #   Period 3: 10:05 - 11:00
    #   Lunch Break (Other Years): 11:00 - 11:30 (30 mins)
    #   Period 4: 11:30 - 12:25
    #   Period 5: 12:25 - 13:20
    #   Period 6: 13:20 - 14:15
    PERIODS_OTHER_YEARS = [
        {"period": 1, "start": "08:15", "end": "09:10", "label": "08:15 – 09:10"},
        {"period": 2, "start": "09:10", "end": "10:05", "label": "09:10 – 10:05"},
        {"period": 3, "start": "10:05", "end": "11:00", "label": "10:05 – 11:00"},
        {"period": 4, "start": "11:30", "end": "12:25", "label": "11:30 – 12:25"},
        {"period": 5, "start": "12:25", "end": "13:20", "label": "12:25 – 13:20"},
        {"period": 6, "start": "13:20", "end": "14:15", "label": "13:20 – 14:15"},
    ]
    LUNCH_OTHER_YEARS = {"start": "11:00", "end": "11:30", "label": "11:00 – 11:30 AM"}

    # Course Selection Limits for Students
    MAX_THEORY_COURSES = 6
    MAX_LAB_COURSES = 4

    # Lab Duration Options (in periods: 2 periods = 110 mins, 3 periods = 165 mins)
    LAB_DURATION_OPTIONS = [2, 3]

