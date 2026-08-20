import os, secrets, random, hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from authlib.integrations.flask_client import OAuth
import requests

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("MONGO_DB", "nep_time_abit")
client = MongoClient(MONGO_URI) if MONGO_URI else None
db = client[DB_NAME] if client else None

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

oauth = OAuth(app)
if os.getenv("GOOGLE_CLIENT_ID"):
    google = oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
else:
    google = None

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
LESSIONS = [
    ("08:15","09:10"), ("09:10","10:05"), ("10:35","11:30"),
    ("11:30","12:25"), ("12:25","13:20"), ("13:20","14:15")
]
LUNCH = {
    1: ("10:05","10:35"),
    "other": ("11:00","11:30")
}

def users():
    return db.users
def courses():
    return db.courses
def timetable():
    return db.timetable
def attendance():
    return db.attendance
def otp_collection():
    return db.otps

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to access this area.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def send_otp_email(email, otp):
    """Send OTP using EmailJS REST API."""

    service_id = os.getenv("EMAILJS_SERVICE_ID")
    template_id = os.getenv("EMAILJS_TEMPLATE_ID")
    public_key = os.getenv("EMAILJS_PUBLIC_KEY")
    private_key = os.getenv("EMAILJS_PRIVATE_KEY")

    if not all([
        service_id,
        template_id,
        public_key,
        private_key
    ]):
        print(f"[DEV OTP] {email}: {otp}")
        return True

    payload = {
        "service_id": service_id,
        "template_id": template_id,

        # EmailJS public key
        "user_id": public_key,

        # EmailJS private key for server-side authorization
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

        print(
            f"[EMAILJS ERROR] HTTP {response.status_code}: "
            f"{response.text}"
        )
        return False

    except requests.RequestException as e:
        print(f"[EMAILJS ERROR] {e}")
        return False
    
@app.context_processor
def inject_globals():
    return {"college": "Ajay Binay Institute of Technology (ABIT)",
            "days": DAYS, "lessions": LESSIONS}

@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email, password = request.form["email"].lower().strip(), request.form["password"]
        u = users().find_one({"email": email, "password": hash_password(password)})
        if not u:
            flash("Invalid email or password.", "danger")
        else:
            session.update(user_id=str(u["_id"]), role=u["role"], email=u["email"], name=u.get("name",""))
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        role = request.form["role"]
        if role not in ["student","teacher"]:
            flash("Only students and teachers can self-register.", "danger")
            return redirect(url_for("register"))
        if users().find_one({"email": email}):
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))
        otp = f"{random.randint(0,999999):06d}"
        otp_collection().delete_many({"email": email})
        otp_collection().insert_one({
            "email": email, "otp": otp, "role": role,
            "expires": datetime.utcnow()+timedelta(minutes=10),
            "payload": {
                "name": request.form["name"],
                "program": request.form.get("program",""),
                "semester": int(request.form.get("semester", 1)),
                "student_group": request.form.get("student_group","")
            }
        })
        send_otp_email(email, otp)
        session["pending_email"] = email
        flash("OTP sent. Check your email.", "success")
        return redirect(url_for("verify_otp"))
    return render_template("register.html")

@app.route("/verify-otp", methods=["GET","POST"])
def verify_otp():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("register"))
    if request.method == "POST":
        rec = otp_collection().find_one({"email": email})
        if not rec or rec["expires"] < datetime.utcnow() or rec["otp"] != request.form["otp"]:
            flash("Invalid or expired OTP.", "danger")
        else:
            p = rec["payload"]
            doc = {
                "email": email, "password": hash_password(request.form["password"]),
                "role": rec["role"], "name": p["name"], "program": p["program"],
                "semester": p["semester"], "student_group": p["student_group"],
                "email_verified": True, "created_at": datetime.utcnow(),
                "avatar": ""
            }
            result = users().insert_one(doc)
            otp_collection().delete_many({"email": email})
            session.update(user_id=str(result.inserted_id), role=rec["role"], email=email, name=p["name"])
            return redirect(url_for("dashboard"))
    return render_template("verify.html", email=email)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/auth/google")
def google_login():
    if not google:
        flash("Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.", "warning")
        return redirect(url_for("login"))
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def google_callback():
    if not google:
        return redirect(url_for("login"))
    token = google.authorize_access_token()
    info = token.get("userinfo")
    if not info:
        info = google.userinfo()
    email = info["email"].lower()
    u = users().find_one({"email": email})
    if not u:
        result = users().insert_one({
            "email": email, "name": info.get("name", email.split("@")[0]),
            "role": "student", "email_verified": True, "avatar": info.get("picture",""),
            "program": "", "semester": 1, "student_group": "", "google_id": info["sub"],
            "created_at": datetime.utcnow()
        })
        uid = result.inserted_id
        role = "student"
    else:
        uid, role = u["_id"], u["role"]
        users().update_one({"_id":uid}, {"$set":{"avatar":info.get("picture",u.get("avatar",""))}})
    session.update(user_id=str(uid), role=role, email=email, name=info.get("name",""))
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required()
def dashboard():
    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))
    if session["role"] == "teacher":
        return redirect(url_for("teacher_dashboard"))
    return redirect(url_for("student_dashboard"))

@app.route("/profile", methods=["GET","POST"])
@login_required()
def profile():
    u = users().find_one({"_id": ObjectId(session["user_id"])})
    if request.method == "POST":
        data = {
            "name": request.form.get("name","").strip(),
            "phone": request.form.get("phone","").strip(),
            "program": request.form.get("program","").strip(),
            "semester": int(request.form.get("semester",1)),
            "student_group": request.form.get("student_group","").strip(),
        }
        pic = request.files.get("avatar")
        if pic and pic.filename:
            result = cloudinary.uploader.upload(pic, folder="nep-time/profiles")
            data["avatar"] = result["secure_url"]
        users().update_one({"_id":u["_id"]},{"$set":data})
        session["name"] = data["name"]
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=u)

@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    stats = {
        "students": users().count_documents({"role":"student"}),
        "teachers": users().count_documents({"role":"teacher"}),
        "courses": courses().count_documents({}),
        "attendance_records": attendance().count_documents({})
    }
    # Graph-ready aggregations
    role_data = list(users().aggregate([{"$group":{"_id":"$role","count":{"$sum":1}}}]))
    category_data = list(courses().aggregate([{"$group":{"_id":"$category","count":{"$sum":1}}}]))
    return render_template("admin.html", stats=stats, role_data=role_data, category_data=category_data)

@app.route("/teacher")
@login_required("teacher")
def teacher_dashboard():
    uid = ObjectId(session["user_id"])
    assigned = list(courses().find({"teacher_id": uid}))
    return render_template("teacher.html", courses=assigned)

@app.route("/student")
@login_required("student")
def student_dashboard():
    u = users().find_one({"_id":ObjectId(session["user_id"])})
    group = u.get("student_group","")
    entries = list(timetable().find({"student_group":group}).sort([("day_index",1),("period",1)]))
    records = list(attendance().find({"student_id":ObjectId(session["user_id"])}))
    return render_template("student.html", user=u, entries=entries, attendance=records)

@app.route("/attendance/<course_id>", methods=["GET","POST"])
@login_required("teacher")
def mark_attendance(course_id):
    course = courses().find_one({"_id":ObjectId(course_id), "teacher_id":ObjectId(session["user_id"])})
    if not course:
        flash("Course not assigned to you.", "danger")
        return redirect(url_for("teacher_dashboard"))
    students = list(users().find({"role":"student","student_group":course["student_group"]}).sort("name",1))
    if request.method == "POST":
        date = request.form["date"]
        for s in students:
            status = request.form.get(f"student_{s['_id']}", "absent")
            attendance().update_one(
                {"student_id":s["_id"], "course_id":course["_id"], "date":date},
                {"$set":{"status":status, "teacher_id":ObjectId(session["user_id"]), "updated_at":datetime.utcnow()}},
                upsert=True
            )
        flash("Attendance saved.", "success")
        return redirect(url_for("mark_attendance", course_id=course_id, date=date))
    return render_template("attendance_mark.html", course=course, students=students,
                           date=request.args.get("date",datetime.utcnow().strftime("%Y-%m-%d")))

@app.route("/student/attendance")
@login_required("student")
def student_attendance():
    uid = ObjectId(session["user_id"])
    rows = list(attendance().find({"student_id":uid}))
    stats = {}
    for r in rows:
        cid = str(r["course_id"])
        stats.setdefault(cid, {"course": r.get("course_name",""), "present":0, "absent":0, "total":0})
        stats[cid]["total"] += 1
        stats[cid][r["status"]] = stats[cid].get(r["status"],0)+1
    for cid in stats:
        x=stats[cid]; x["percent"]=round(x["present"]/x["total"]*100,1) if x["total"] else 0
    return render_template("attendance_student.html", stats=list(stats.values()), rows=rows)

@app.route("/api/attendance")
@login_required("student")
def api_attendance():
    rows = list(attendance().find({"student_id":ObjectId(session["user_id"])}))
    for r in rows: r["_id"] = str(r["_id"]); r["student_id"] = str(r["student_id"]); r["course_id"] = str(r["course_id"])
    return jsonify(rows)

@app.route("/api/courses")
@login_required()
def api_courses():
    return jsonify([{"id":str(c["_id"]), "name":c["name"], "code":c["code"],
                    "type":c.get("type","theory"), "category":c.get("category","Major")}
                   for c in courses().find({})])

if __name__ == "__main__":
    app.run(debug=True)
