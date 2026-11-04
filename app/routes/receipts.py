import os
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.receipt import ReceiptScan
from app.services.receipt_service import ReceiptScannerService
from app.services.categorizer_service import CategorizerService
from app.services.anomaly_service import AnomalyDetectionService

receipts_bp = Blueprint("receipts", __name__)

@receipts_bp.route("/")
def index():
    scans = ReceiptScan.query.order_by(ReceiptScan.created_at.desc()).all()
    return render_template("receipts.html", scans=scans)

@receipts_bp.route("/upload", methods=["POST"])
def upload_receipt():
    if "receipt_image" not in request.files:
        flash("No receipt image selected.", "danger")
        return redirect(url_for("receipts.index"))

    file = request.files["receipt_image"]
    if not file or not file.filename:
        flash("Please select a valid image file.", "danger")
        return redirect(url_for("receipts.index"))

    if not ReceiptScannerService.is_allowed_file(file.filename):
        flash("Unsupported file format. Supported: PNG, JPG, JPEG, WEBP, BMP.", "danger")
        return redirect(url_for("receipts.index"))

    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        scan = ReceiptScannerService.process_receipt_upload(file, upload_folder)
        flash("Receipt scanned successfully! Please review the extracted information before saving.", "info")
        return redirect(url_for("receipts.confirm_receipt", scan_id=scan.id))
    except Exception as e:
        flash(f"Error processing receipt: {str(e)}", "danger")
        return redirect(url_for("receipts.index"))

@receipts_bp.route("/<int:scan_id>/confirm", methods=["GET", "POST"])
def confirm_receipt(scan_id):
    scan = ReceiptScan.query.get_or_404(scan_id)
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        merchant = request.form.get("merchant", "").strip() or scan.extracted_merchant
        description = request.form.get("description", "").strip() or f"Receipt purchase from {merchant}"
        amount_str = request.form.get("amount", "0").replace(",", "").strip()
        date_str = request.form.get("date", "").strip()
        category_id = request.form.get("category_id", type=int)
        notes = request.form.get("notes", "").strip() or None

        try:
            amount = abs(float(amount_str))
            tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid amount or date format.", "danger")
            return redirect(url_for("receipts.confirm_receipt", scan_id=scan.id))

        # Category check
        if not category_id:
            sug = CategorizerService.suggest_category(f"{merchant} {description}", amount)
            category_id = sug["category_id"]

        # Anomaly evaluation
        is_anom, score, reason, _ = AnomalyDetectionService.evaluate_transaction(
            amount=amount,
            category_id=category_id,
            trans_date=tx_date,
            transaction_type="expense"
        )

        tx = Transaction(
            amount=amount,
            transaction_type="expense",
            date=tx_date,
            description=description,
            merchant=merchant,
            category_id=category_id,
            receipt_scan_id=scan.id,
            is_anomaly=is_anom,
            anomaly_score=score,
            anomaly_reason=reason,
            notes=notes or f"Verified from receipt scan: {scan.original_filename}",
        )
        scan.status = "confirmed"
        db.session.add(tx)
        db.session.commit()

        flash(f"Transaction successfully confirmed and created from receipt!", "success")
        return redirect(url_for("core.transactions"))

    # Auto-suggest category for display in confirmation screen
    combined_desc = f"{scan.extracted_merchant or ''} Receipt"
    suggestion = CategorizerService.suggest_category(combined_desc, scan.extracted_amount or 0.0)

    return render_template(
        "receipt_confirm.html",
        scan=scan,
        categories=categories,
        suggested_category=suggestion,
    )

@receipts_bp.route("/<int:scan_id>/discard", methods=["POST"])
def discard_receipt(scan_id):
    scan = ReceiptScan.query.get_or_404(scan_id)
    scan.status = "discarded"
    db.session.commit()
    flash("Receipt scan discarded.", "info")
    return redirect(url_for("receipts.index"))

