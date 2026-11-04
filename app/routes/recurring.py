from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.models.category import Category
from app.models.recurring import RecurringRule
from app.services.recurring_service import RecurringService

recurring_bp = Blueprint("recurring", __name__)

@recurring_bp.route("/")
def index():
    rules = RecurringRule.query.order_by(RecurringRule.is_active.desc(), RecurringRule.next_due_date).all()
    upcoming = RecurringService.get_upcoming_payments(days_ahead=30)
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "recurring.html",
        rules=rules,
        upcoming=upcoming,
        categories=categories,
    )

@recurring_bp.route("/new", methods=["GET", "POST"])
def add_rule():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        merchant = request.form.get("merchant", "").strip() or None
        amount_str = request.form.get("amount", "0").replace(",", "").strip()
        frequency = request.form.get("frequency", "monthly").lower()
        interval = request.form.get("interval", 1, type=int)
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip() or None
        category_id = request.form.get("category_id", type=int)
        tx_type = request.form.get("transaction_type", "expense")

        if not description or not amount_str or not start_date_str or not category_id:
            flash("Description, amount, category, and start date are required.", "danger")
            return redirect(url_for("recurring.add_rule"))

        try:
            amount = abs(float(amount_str))
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
        except ValueError:
            flash("Invalid amount or date format.", "danger")
            return redirect(url_for("recurring.add_rule"))

        RecurringService.create_rule(
            description=description,
            amount=amount,
            category_id=category_id,
            frequency=frequency,
            start_date=start_date,
            interval=interval,
            end_date=end_date,
            merchant=merchant,
            transaction_type=tx_type,
        )
        flash("Recurring schedule created successfully!", "success")
        return redirect(url_for("recurring.index"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("recurring_form.html", rule=None, categories=categories, today=date.today())

@recurring_bp.route("/<int:rule_id>/edit", methods=["GET", "POST"])
def edit_rule(rule_id):
    rule = RecurringRule.query.get_or_404(rule_id)
    if request.method == "POST":
        rule.description = request.form.get("description", "").strip()
        rule.merchant = request.form.get("merchant", "").strip() or None
        rule.category_id = request.form.get("category_id", type=int)
        rule.frequency = request.form.get("frequency", "monthly").lower()
        rule.interval = request.form.get("interval", 1, type=int)
        rule.transaction_type = request.form.get("transaction_type", "expense")
        rule.is_active = True if request.form.get("is_active") == "on" else False

        amount_str = request.form.get("amount", "0").replace(",", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip() or None

        try:
            rule.amount = abs(float(amount_str))
            rule.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            rule.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
        except ValueError:
            flash("Invalid date or amount format.", "danger")
            return redirect(url_for("recurring.edit_rule", rule_id=rule.id))

        db.session.commit()
        flash("Recurring schedule updated successfully.", "success")
        return redirect(url_for("recurring.index"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("recurring_form.html", rule=rule, categories=categories, today=date.today())

@recurring_bp.route("/<int:rule_id>/toggle", methods=["POST"])
def toggle_rule(rule_id):
    rule = RecurringRule.query.get_or_404(rule_id)
    rule.is_active = not rule.is_active
    db.session.commit()
    status_str = "resumed" if rule.is_active else "paused"
    flash(f"Recurring schedule '{rule.description}' has been {status_str}.", "info")
    return redirect(url_for("recurring.index"))

@recurring_bp.route("/<int:rule_id>/delete", methods=["POST"])
def delete_rule(rule_id):
    rule = RecurringRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash("Recurring rule deleted.", "info")
    return redirect(url_for("recurring.index"))

@recurring_bp.route("/process-due", methods=["POST"])
def process_due():
    created = RecurringService.process_due_transactions(as_of_date=date.today())
    if created:
        flash(f"Processed {len(created)} recurring transaction(s) due as of today.", "success")
    else:
        flash("All recurring transactions are up to date! None due today.", "info")
    return redirect(url_for("recurring.index"))

