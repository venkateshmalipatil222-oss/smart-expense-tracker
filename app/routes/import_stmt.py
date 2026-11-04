import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.models.import_batch import ImportBatch
from app.services.import_service import ImportService

import_bp = Blueprint("import_stmt", __name__)

@import_bp.route("/")
def index():
    batches = ImportBatch.query.order_by(ImportBatch.created_at.desc()).all()
    return render_template("import.html", batches=batches)

@import_bp.route("/upload", methods=["POST"])
def upload_file():
    if "statement_file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("import_stmt.index"))

    file = request.files["statement_file"]
    if not file or not file.filename:
        flash("Please choose a valid CSV or Excel file.", "danger")
        return redirect(url_for("import_stmt.index"))

    if not ImportService.is_allowed_file(file.filename):
        flash("Unsupported format. Please upload a .CSV, .XLSX, or .XLS file.", "danger")
        return redirect(url_for("import_stmt.index"))

    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        filepath, original_name, columns, sample_rows = ImportService.parse_uploaded_file(file, upload_folder)
        auto_mapping = ImportService.auto_detect_column_mapping(columns)

        # Store in session for the mapping workflow
        session["import_filepath"] = filepath
        session["import_filename"] = original_name
        session["import_columns"] = columns

        return render_template(
            "import_mapping.html",
            filename=original_name,
            columns=columns,
            sample_rows=sample_rows[:5],
            auto_mapping=auto_mapping,
        )
    except Exception as e:
        flash(f"Failed to read file: {str(e)}", "danger")
        return redirect(url_for("import_stmt.index"))

@import_bp.route("/preview", methods=["POST"])
def preview():
    filepath = session.get("import_filepath")
    filename = session.get("import_filename")

    if not filepath or not os.path.exists(filepath):
        flash("Import session expired. Please re-upload your statement.", "warning")
        return redirect(url_for("import_stmt.index"))

    date_col = request.form.get("date_col")
    desc_col = request.form.get("desc_col")
    amount_col = request.form.get("amount_col")
    cat_col = request.form.get("cat_col", "")

    if not date_col or not desc_col or not amount_col:
        flash("Please map Date, Description, and Amount columns.", "danger")
        return redirect(url_for("import_stmt.index"))

    # Save mapping choices in session
    session["map_date_col"] = date_col
    session["map_desc_col"] = desc_col
    session["map_amount_col"] = amount_col
    session["map_cat_col"] = cat_col

    preview_rows = ImportService.preview_with_duplicates(
        filepath=filepath,
        date_col=date_col,
        desc_col=desc_col,
        amount_col=amount_col,
        cat_col=cat_col
    )

    duplicate_count = sum(1 for r in preview_rows if r["is_duplicate"])

    return render_template(
        "import_preview.html",
        filename=filename,
        rows=preview_rows,
        total_rows=len(preview_rows),
        duplicate_count=duplicate_count,
    )

@import_bp.route("/commit", methods=["POST"])
def commit_import():
    filepath = session.get("import_filepath")
    filename = session.get("import_filename", "statement.csv")
    date_col = session.get("map_date_col")
    desc_col = session.get("map_desc_col")
    amount_col = session.get("map_amount_col")
    cat_col = session.get("map_cat_col", "")
    skip_dups = True if request.form.get("skip_duplicates") == "on" else False

    if not filepath or not os.path.exists(filepath):
        flash("Import session expired. Please re-upload your statement.", "warning")
        return redirect(url_for("import_stmt.index"))

    try:
        batch = ImportService.commit_import(
            filepath=filepath,
            original_filename=filename,
            date_col=date_col,
            desc_col=desc_col,
            amount_col=amount_col,
            cat_col=cat_col,
            skip_duplicates=skip_dups
        )
        flash(
            f"Successfully imported {batch.imported_rows} transactions from {filename} "
            f"({batch.skipped_duplicates} duplicate records safely skipped)!",
            "success"
        )
    except Exception as e:
        flash(f"Error executing statement import: {str(e)}", "danger")

    return redirect(url_for("core.transactions"))

