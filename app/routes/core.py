from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.insight_service import InsightService
from app.services.categorizer_service import CategorizerService
from app.services.anomaly_service import AnomalyDetectionService
from app.services.recurring_service import RecurringService

core_bp = Blueprint("core", __name__)

@core_bp.route("/")
def dashboard():
    today = date.today()
    overview = InsightService.get_spending_overview(today)
    recommendations = InsightService.generate_recommendations(today)
    upcoming_payments = RecurringService.get_upcoming_payments(days_ahead=14)
    
    # Recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(10).all()
    
    # Recent anomalies
    recent_anomalies = Transaction.query.filter_by(is_anomaly=True).order_by(Transaction.date.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        overview=overview,
        recommendations=recommendations[:3],  # Top 3 highlights
        upcoming_payments=upcoming_payments,
        recent_transactions=recent_transactions,
        recent_anomalies=recent_anomalies,
    )

@core_bp.route("/transactions")
def transactions():
    query = Transaction.query
    
    category_id = request.args.get("category_id", type=int)
    tx_type = request.args.get("type")
    is_anomaly = request.args.get("is_anomaly")
    search = request.args.get("search", "").strip()
    
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if tx_type in ["expense", "income"]:
        query = query.filter(Transaction.transaction_type == tx_type)
    if is_anomaly == "1":
        query = query.filter(Transaction.is_anomaly == True)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%") | Transaction.merchant.ilike(f"%{search}%"))
        
    transactions_list = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "transactions.html",
        transactions=transactions_list,
        categories=categories,
        selected_category=category_id,
        selected_type=tx_type,
        selected_anomaly=is_anomaly,
        search_query=search,
    )

@core_bp.route("/transactions/new", methods=["GET", "POST"])
def add_transaction():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        merchant = request.form.get("merchant", "").strip() or None
        amount_str = request.form.get("amount", "0").replace(",", "").strip()
        date_str = request.form.get("date", "").strip()
        category_id = request.form.get("category_id", type=int)
        tx_type = request.form.get("transaction_type", "expense")
        notes = request.form.get("notes", "").strip() or None

        if not description or not amount_str or not date_str:
            flash("Description, amount, and date are required.", "danger")
            return redirect(url_for("core.add_transaction"))

        try:
            amount = abs(float(amount_str))
            tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid amount or date format.", "danger")
            return redirect(url_for("core.add_transaction"))

        # Category resolution or auto-suggestion
        if not category_id:
            sug = CategorizerService.suggest_category(description, amount)
            category_id = sug["category_id"]

        # Anomaly detection evaluation
        is_anom, score, reason, method = AnomalyDetectionService.evaluate_transaction(
            amount=amount,
            category_id=category_id,
            trans_date=tx_date,
            transaction_type=tx_type
        )

        tx = Transaction(
            amount=amount,
            transaction_type=tx_type,
            date=tx_date,
            description=description,
            merchant=merchant,
            category_id=category_id,
            is_anomaly=is_anom,
            anomaly_score=score,
            anomaly_reason=reason,
            notes=notes,
        )
        db.session.add(tx)
        db.session.commit()

        if is_anom:
            flash(f"Transaction recorded! Note: Flagged as an Unusual Expense ({reason})", "warning")
        else:
            flash("Transaction recorded successfully!", "success")

        return redirect(url_for("core.transactions"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("transaction_form.html", transaction=None, categories=categories, today=date.today())

@core_bp.route("/transactions/<int:tx_id>/edit", methods=["GET", "POST"])
def edit_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    if request.method == "POST":
        tx.description = request.form.get("description", "").strip()
        tx.merchant = request.form.get("merchant", "").strip() or None
        tx.category_id = request.form.get("category_id", type=int)
        tx.transaction_type = request.form.get("transaction_type", "expense")
        tx.notes = request.form.get("notes", "").strip() or None
        
        amount_str = request.form.get("amount", "0").replace(",", "").strip()
        date_str = request.form.get("date", "").strip()
        try:
            tx.amount = abs(float(amount_str))
            tx.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid amount or date format.", "danger")
            return redirect(url_for("core.edit_transaction", tx_id=tx.id))

        # Re-evaluate anomaly
        is_anom, score, reason, _ = AnomalyDetectionService.evaluate_transaction(
            amount=tx.amount,
            category_id=tx.category_id,
            trans_date=tx.date,
            transaction_type=tx.transaction_type,
            exclude_tx_id=tx.id
        )
        tx.is_anomaly = is_anom
        tx.anomaly_score = score
        tx.anomaly_reason = reason

        db.session.commit()
        flash("Transaction updated successfully.", "success")
        return redirect(url_for("core.transactions"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("transaction_form.html", transaction=tx, categories=categories, today=date.today())

@core_bp.route("/transactions/<int:tx_id>/delete", methods=["POST"])
def delete_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    db.session.delete(tx)
    db.session.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("core.transactions"))

@core_bp.route("/api/categorize")
def api_categorize():
    """
    Live API for interactive auto-categorization suggestions as user types.
    """
    desc = request.args.get("description", "")
    amount = request.args.get("amount", 0.0, type=float)
    suggestion = CategorizerService.suggest_category(desc, amount)
    return jsonify(suggestion)

@core_bp.route("/api/check-anomaly")
def api_check_anomaly():
    """
    Live API for client-side anomaly alert preview before submission.
    """
    amount = request.args.get("amount", 0.0, type=float)
    cat_id = request.args.get("category_id", type=int)
    date_str = request.args.get("date", "")
    try:
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        t_date = date.today()

    if not cat_id or amount <= 0:
        return jsonify({"is_anomaly": False, "score": 0.0, "reason": None})

    is_anom, score, reason, method = AnomalyDetectionService.evaluate_transaction(
        amount=amount,
        category_id=cat_id,
        trans_date=t_date,
        transaction_type="expense"
    )
    return jsonify({
        "is_anomaly": is_anom,
        "score": score,
        "reason": reason,
        "method": method
    })

