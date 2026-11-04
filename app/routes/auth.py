import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.database import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()
        remember = True if request.form.get("remember") == "on" else False

        if not identifier or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template("auth/login.html")

        # Find user by username or email
        user = User.query.filter(
            (User.username.ilike(identifier)) | (User.email.ilike(identifier))
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page if next_page else url_for("core.dashboard"))
        else:
            flash("Invalid credentials. Please verify your username/email and password.", "danger")

    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "danger")
            return render_template("auth/register.html")

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Email is already registered. Please login instead.", "danger")
            return render_template("auth/register.html")

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f"Account created successfully! Welcome to Smart Expense Tracker, {username}.", "success")
        return redirect(url_for("core.dashboard"))

    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))

