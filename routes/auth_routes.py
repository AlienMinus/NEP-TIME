import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from bson import ObjectId
from database import get_users_col
from services.auth_service import (
    hash_password,
    create_otp_request,
    verify_and_create_user,
    get_google_oauth,
    login_required
)
from config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("auth.dashboard_redirect"))
    return render_template("landing.html")

@auth_bp.route("/dashboard")
@login_required()
def dashboard_redirect():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    elif role == "teacher":
        return redirect(url_for("teacher.dashboard"))
    elif role == "student":
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("auth.dashboard_redirect"))

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        users = get_users_col()
        user = users.find_one({"email": email, "password": hash_password(password)})

        if not user:
            flash("Invalid email or password. Please check your credentials.", "danger")
        else:
            session.clear()
            session.update({
                "user_id": str(user["_id"]),
                "role": user.get("role", "student"),
                "email": user.get("email"),
                "name": user.get("name", ""),
                "avatar": user.get("avatar", ""),
                "student_group": user.get("student_group", ""),
                "regn_no": user.get("regn_no", ""),
                "employee_id": user.get("employee_id", "")
            })
            flash(f"Welcome back, {user.get('name', 'User')}!", "success")
            return redirect(url_for("auth.dashboard_redirect"))

    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("auth.dashboard_redirect"))

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        role = request.form.get("role", "student")

        if role not in ["student", "teacher"]:
            flash("Registration is only open for Students and Teachers.", "danger")
            return redirect(url_for("auth.register"))

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        program = request.form.get("program", "Electrical & Computer Engineering").strip()
        semester = int(request.form.get("semester", 1))
        student_group = request.form.get("student_group", "ECE-6A").strip()
        regn_no = request.form.get("regn_no", "").strip()
        employee_id = request.form.get("employee_id", "").strip()
        designation = request.form.get("designation", "Assistant Professor").strip()

        payload = {
            "name": name,
            "phone": phone,
            "program": program,
            "semester": semester,
            "student_group": student_group,
            "regn_no": regn_no,
            "employee_id": employee_id,
            "designation": designation
        }

        success, msg = create_otp_request(email, role, payload)
        if not success:
            flash(msg, "danger")
            return redirect(url_for("auth.register"))

        session["pending_email"] = email
        session["pending_role"] = role
        flash("Verification OTP sent! Please check your email inbox.", "success")
        return redirect(url_for("auth.verify_otp"))

    return render_template("register.html")

@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("verify.html", email=email)

        success, res = verify_and_create_user(email, otp, password)
        if not success:
            flash(res, "danger")
            return render_template("verify.html", email=email)

        # Log the user in directly
        users = get_users_col()
        user = users.find_one({"_id": res})

        session.clear()
        session.update({
            "user_id": str(user["_id"]),
            "role": user.get("role", "student"),
            "email": user.get("email"),
            "name": user.get("name", ""),
            "avatar": user.get("avatar", ""),
            "student_group": user.get("student_group", ""),
            "regn_no": user.get("regn_no", ""),
            "employee_id": user.get("employee_id", "")
        })
        flash("Account created and verified successfully! Welcome to NEP-TIME ABIT.", "success")
        return redirect(url_for("auth.dashboard_redirect"))

    return render_template("verify.html", email=email)

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.index"))

@auth_bp.route("/auth/google")
def google_login():
    google = get_google_oauth()
    if not google:
        flash("Google OAuth is not configured in this environment.", "warning")
        return redirect(url_for("auth.login"))

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", url_for("auth.google_callback", _external=True))
    return google.authorize_redirect(redirect_uri)

@auth_bp.route("/auth/google/callback")
def google_callback():
    google = get_google_oauth()
    if not google:
        return redirect(url_for("auth.login"))

    try:
        token = google.authorize_access_token()
        info = token.get("userinfo") or google.userinfo()
        if not info:
            flash("Failed to retrieve Google profile.", "danger")
            return redirect(url_for("auth.login"))

        email = info["email"].lower().strip()
        users = get_users_col()
        user = users.find_one({"email": email})

        if not user:
            # Create user as student by default
            new_user = {
                "email": email,
                "name": info.get("name", email.split("@")[0]),
                "role": "student",
                "email_verified": True,
                "avatar": info.get("picture", ""),
                "program": "Engineering",
                "semester": 1,
                "student_group": "ECE-1A",
                "regn_no": "",
                "employee_id": "",
                "google_id": info.get("sub"),
                "created_at": datetime.utcnow()
            }
            res = users.insert_one(new_user)
            uid = res.inserted_id
            role = "student"
            name = new_user["name"]
            avatar = new_user["avatar"]
            group = new_user["student_group"]
            regn = ""
            empid = ""
        else:
            uid = user["_id"]
            role = user.get("role", "student")
            name = user.get("name", info.get("name", ""))
            avatar = user.get("avatar") or info.get("picture", "")
            group = user.get("student_group", "")
            regn = user.get("regn_no", "")
            empid = user.get("employee_id", "")
            users.update_one({"_id": uid}, {"$set": {"google_id": info.get("sub"), "email_verified": True}})

        session.clear()
        session.update({
            "user_id": str(uid),
            "role": role,
            "email": email,
            "name": name,
            "avatar": avatar,
            "student_group": group,
            "regn_no": regn,
            "employee_id": empid
        })
        flash(f"Signed in via Google as {name}.", "success")
        return redirect(url_for("auth.dashboard_redirect"))

    except Exception as e:
        print(f"[GOOGLE AUTH ERROR] {e}")
        flash("Google authentication encountered an error. Please try standard login.", "danger")
        return redirect(url_for("auth.login"))

