import os
import random
import hashlib
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash
from authlib.integrations.flask_client import OAuth
from database import get_users_col, get_otps_col
from config import Config

oauth = None
google_oauth = None

def init_oauth(app):
    global oauth, google_oauth
    oauth = OAuth(app)
    client_id = os.getenv("GOOGLE_CLIENT_ID", Config.GOOGLE_CLIENT_ID)
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", Config.GOOGLE_CLIENT_SECRET)
    if client_id and client_secret:
        google_oauth = oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    else:
        google_oauth = None
    return google_oauth

def get_google_oauth():
    global google_oauth
    return google_oauth

def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()

def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"

def send_otp_email(email: str, otp: str) -> bool:
    """Send OTP using EmailJS REST API."""
    service_id = os.getenv("EMAILJS_SERVICE_ID", Config.EMAILJS_SERVICE_ID)
    template_id = os.getenv("EMAILJS_TEMPLATE_ID", Config.EMAILJS_TEMPLATE_ID)
    public_key = os.getenv("EMAILJS_PUBLIC_KEY", Config.EMAILJS_PUBLIC_KEY)
    private_key = os.getenv("EMAILJS_PRIVATE_KEY", Config.EMAILJS_PRIVATE_KEY)

    if not all([service_id, template_id, public_key, private_key]):
        print(f"[DEV OTP FALLBACK] OTP for {email}: {otp}")
        return True

    payload = {
        "service_id": service_id,
        "template_id": template_id,
        "user_id": public_key,
        "accessToken": private_key,
        "template_params": {
            "to_email": email,
            "otp": otp,
            "app_name": "NEP-TIME ABIT"
        }
    }

    try:
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=payload,
            timeout=15
        )
        if response.ok:
            print(f"[EMAILJS] OTP sent to {email}")
            return True
        print(f"[EMAILJS ERROR] HTTP {response.status_code}: {response.text}")
        print(f"[DEV OTP FALLBACK] OTP for {email}: {otp}")
        return False
    except requests.RequestException as e:
        print(f"[EMAILJS EXCEPTION] {e}")
        print(f"[DEV OTP FALLBACK] OTP for {email}: {otp}")
        return False

def create_otp_request(email: str, role: str, payload: dict) -> tuple[bool, str]:
    users = get_users_col()
    if users.find_one({"email": email.lower().strip()}):
        return False, "Email is already registered. Please sign in."

    otp = generate_otp()
    otps = get_otps_col()
    otps.delete_many({"email": email.lower().strip()})
    otps.insert_one({
        "email": email.lower().strip(),
        "otp": otp,
        "role": role,
        "expires": datetime.utcnow() + timedelta(minutes=10),
        "payload": payload,
        "created_at": datetime.utcnow()
    })
    send_otp_email(email.lower().strip(), otp)
    return True, "OTP sent to your email."

def verify_and_create_user(email: str, otp: str, password: str):
    email = email.lower().strip()
    otps = get_otps_col()
    users = get_users_col()
    rec = otps.find_one({"email": email})
    
    if not rec:
        return False, "No pending registration found for this email."
    if rec["expires"] < datetime.utcnow():
        return False, "OTP has expired. Please register again."
    if rec["otp"] != otp.strip():
        return False, "Invalid OTP code entered."

    p = rec["payload"]
    user_doc = {
        "email": email,
        "password": hash_password(password),
        "role": rec["role"],
        "name": p.get("name", "").strip(),
        "phone": p.get("phone", "").strip(),
        "program": p.get("program", "").strip(),
        "semester": int(p.get("semester", 1)),
        "student_group": p.get("student_group", "").strip(),
        "regn_no": p.get("regn_no", "").strip(),
        "employee_id": p.get("employee_id", "").strip(),
        "designation": p.get("designation", "").strip(),
        "teaching_subjects": [],
        "email_verified": True,
        "avatar": "",
        "created_at": datetime.utcnow()
    }
    
    result = users.insert_one(user_doc)
    otps.delete_many({"email": email})
    return True, result.inserted_id

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if role and session.get("role") != role:
                flash("You do not have permission to access this area.", "danger")
                return redirect(url_for("auth.dashboard_redirect"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

