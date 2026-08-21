import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson import ObjectId
from database import get_users_col
from services.auth_service import login_required
from config import Config

profile_bp = Blueprint("profile", __name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", Config.CLOUDINARY_CLOUD_NAME),
    api_key=os.getenv("CLOUDINARY_API_KEY", Config.CLOUDINARY_API_KEY),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", Config.CLOUDINARY_API_SECRET),
    secure=True
)

@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required()
def view_profile():
    uid = session["user_id"]
    users_col = get_users_col()
    user = users_col.find_one({"_id": ObjectId(uid)})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        program = request.form.get("program", "").strip()

        update_data = {
            "name": name,
            "phone": phone,
            "program": program,
        }

        role = user.get("role", "student")
        if role == "student":
            update_data["semester"] = int(request.form.get("semester", 1))
            update_data["student_group"] = request.form.get("student_group", "").strip()
            update_data["regn_no"] = request.form.get("regn_no", "").strip()
        elif role == "teacher":
            update_data["employee_id"] = request.form.get("employee_id", "").strip()
            update_data["designation"] = request.form.get("designation", "").strip()

        # Handle Cloudinary avatar upload
        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            try:
                upload_res = cloudinary.uploader.upload(
                    avatar_file,
                    folder="nep-time/profiles",
                    transformation=[{"width": 400, "height": 400, "crop": "fill", "gravity": "face"}]
                )
                update_data["avatar"] = upload_res.get("secure_url", "")
                session["avatar"] = update_data["avatar"]
            except Exception as e:
                print(f"[CLOUDINARY ERROR] {e}")
                flash("Image upload failed. Please try a different image format.", "warning")

        users_col.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        session["name"] = name
        if "student_group" in update_data:
            session["student_group"] = update_data["student_group"]
        if "regn_no" in update_data:
            session["regn_no"] = update_data["regn_no"]
        if "employee_id" in update_data:
            session["employee_id"] = update_data["employee_id"]

        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.view_profile"))

    return render_template("profile.html", user=user)

