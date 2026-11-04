from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.services.split_service import SplitService
from app.models.transaction import Transaction
from app.models.category import Category

splits_bp = Blueprint("splits", __name__, url_prefix="/splits")

@splits_bp.route("/")
def index():
    summary = SplitService.get_sharing_summary()
    recent_expenses = Transaction.query.filter_by(transaction_type="expense").order_by(Transaction.date.desc()).limit(25).all()
    categories = Category.query.all()

    return render_template(
        "splits.html",
        summary=summary,
        recent_expenses=recent_expenses,
        categories=categories
    )

@splits_bp.route("/settle/<int:share_id>", methods=["POST"])
def settle(share_id):
    try:
        SplitService.settle_share(share_id)
        if request.is_json:
            return jsonify({"success": True, "message": "Share marked as settled."})
        flash("Expense share successfully settled!", "success")
    except ValueError as e:
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 400
        flash(str(e), "error")

    return redirect(url_for("splits.index"))

@splits_bp.route("/unsettle/<int:share_id>", methods=["POST"])
def unsettle(share_id):
    try:
        SplitService.unsettle_share(share_id)
        if request.is_json:
            return jsonify({"success": True, "message": "Share marked as pending."})
        flash("Expense share reverted to pending.", "info")
    except ValueError as e:
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 400
        flash(str(e), "error")

    return redirect(url_for("splits.index"))

@splits_bp.route("/api/transaction/<int:tx_id>/splits", methods=["POST"])
def api_save_splits(tx_id):
    data = request.get_json(silent=True) or {}
    splits_list = data.get("splits", [])
    try:
        res = SplitService.apply_itemized_splits(tx_id, splits_list)
        return jsonify(res)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@splits_bp.route("/api/transaction/<int:tx_id>/shares", methods=["POST"])
def api_save_shares(tx_id):
    data = request.get_json(silent=True) or {}
    shares_list = data.get("shares", [])
    try:
        res = SplitService.apply_expense_shares(tx_id, shares_list)
        return jsonify(res)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@splits_bp.route("/api/summary")
def api_summary():
    summary = SplitService.get_sharing_summary()
    return jsonify(summary)

