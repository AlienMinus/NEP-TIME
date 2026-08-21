# NEP-TIME ABIT Edition

AI-assisted, student-centric timetable and attendance platform for
Ajay Binay Institute of Technology (ABIT).

## Default ABIT academic configuration

- Academic day: 08:15 AM – 02:15 PM
- 6 lessons/day
- Each lesson: 55 minutes
- First-year lunch: 10:05 AM – 10:35 AM
- Other years lunch: 11:00 AM – 11:30 AM
- Labs: configurable as 2-hour or 3-hour blocks

## Authentication

- Admin login
- Student login
- Teacher login
- Student/teacher self-registration
- EmailJS OTP verification
- Google OAuth
- Editable profile
- Cloudinary profile image storage

Google OAuth users default to `student`; an administrator can promote them
to teacher/admin through the admin management layer that should be added
before production deployment.

## Data storage

All textual application data is designed for MongoDB Atlas.
Profile images are uploaded to Cloudinary.

## Run

Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# fill .env
python run.py
```

Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill .env
python run.py
```

Open http://127.0.0.1:8080

## Important production configuration

1. Create MongoDB Atlas database and network/user credentials.
2. Create Cloudinary API credentials.
3. Create an EmailJS service/template. The template should accept:
   `to_email`, `otp`, and `app_name`.
4. Create Google OAuth credentials.
5. Add redirect URI:
   `http://127.0.0.1:8080/auth/google/callback`
   and replace it with your HTTPS production callback after deployment.
6. Change SECRET_KEY.
7. Create the first admin account directly in MongoDB with:
   role = "admin"

## Security

This project is a development-ready foundation, not a security audit.
Before public deployment add CSRF protection, rate limiting, secure cookies,
password hashing with Argon2/bcrypt, audit logs, strict upload validation,
Google account role approval, and HTTPS-only cookies.

## Folder Struture

NEP-TIME-ABIT-Flask-MongoDB-Cloudinary-OAuth/
├── app.py
├── config.py
├── database.py
├── run.py
├── requirements.txt
├── routes/
│   ├── admin_routes.py
│   ├── api_routes.py
│   ├── auth_routes.py
│   ├── profile_routes.py
│   ├── student_routes.py
│   └── teacher_routes.py
├── services/
│   ├── attendance_service.py
│   ├── auth_service.py
│   ├── course_service.py
│   └── timetable_service.py
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    ├── admin/
    │   ├── dashboard.html
    │   ├── faculty_assign.html
    │   ├── subject_edit.html
    │   ├── subjects.html
    │   └── timetable.html
    ├── teacher/
    │   ├── attendance_mark.html
    │   └── dashboard.html
    ├── student/
    │   ├── attendance.html
    │   ├── course_select.html
    │   └── dashboard.html
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── profile.html
    ├── register.html
    └── verify.html