from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import db
from app.models.category import Category
from app.models.goal import FinancialGoal, GoalContribution
from app.services.goal_service import GoalService

goals_bp = Blueprint("goals", __name__)

@goals_bp.route("/")
def index():
    summary = GoalService.get_goals_overview()
    categories = Category.query.order_by(Category.name).all()
    return render_template("goals.html", summary=summary, categories=categories)

@goals_bp.route("/new", methods=["GET", "POST"])
def add_goal():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        target_amount_str = request.form.get("target_amount", "0").replace(",", "").strip()
        current_amount_str = request.form.get("current_amount", "0").replace(",", "").strip()
        target_date_str = request.form.get("target_date", "").strip()
        category_id = request.form.get("category_id", type=int)

        if not title or not target_amount_str or not target_date_str:
            flash("Title, target amount, and target deadline are required.", "danger")
            return redirect(url_for("goals.add_goal"))

        try:
            target_amount = abs(float(target_amount_str))
            current_amount = max(0.0, float(current_amount_str))
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid amount or target date format.", "danger")
            return redirect(url_for("goals.add_goal"))

        goal = GoalService.create_goal(
            title=title,
            target_amount=target_amount,
            target_date=target_date,
            current_amount=current_amount,
            description=description,
            category_id=category_id,
        )
        flash(f"Savings goal '{goal.title}' created successfully!", "success")
        return redirect(url_for("goals.index"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("goal_form.html", goal=None, categories=categories, today=date.today())

@goals_bp.route("/<int:goal_id>")
def goal_detail(goal_id):
    goal = FinancialGoal.query.get_or_404(goal_id)
    contributions = goal.contributions.order_by(GoalContribution.date.desc()).all()
    trajectory = GoalService.get_goal_trajectory(goal.id)

    today = date.today()
    days_left = (goal.target_date - today).days
    months_left = max(1.0, days_left / 30.4)
    monthly_required = (goal.remaining_amount / months_left) if goal.remaining_amount > 0 else 0.0

    return render_template(
        "goal_detail.html",
        goal=goal,
        contributions=contributions,
        trajectory=trajectory,
        monthly_required=round(monthly_required, 2),
        today=today,
    )

@goals_bp.route("/<int:goal_id>/contribute", methods=["POST"])
def add_contribution(goal_id):
    amount_str = request.form.get("amount", "0").replace(",", "").strip()
    date_str = request.form.get("date", "").strip()
    notes = request.form.get("notes", "").strip() or None

    try:
        amount = abs(float(amount_str))
        c_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        flash("Invalid amount or date.", "danger")
        return redirect(url_for("goals.goal_detail", goal_id=goal_id))

    GoalService.record_contribution(goal_id, amount, c_date, notes)
    flash(f"Successfully recorded ${amount:,.2f} contribution toward your goal!", "success")
    return redirect(url_for("goals.goal_detail", goal_id=goal_id))

@goals_bp.route("/<int:goal_id>/delete", methods=["POST"])
def delete_goal(goal_id):
    goal = FinancialGoal.query.get_or_404(goal_id)
    db.session.delete(goal)
    db.session.commit()
    flash("Savings goal deleted.", "info")
    return redirect(url_for("goals.index"))

