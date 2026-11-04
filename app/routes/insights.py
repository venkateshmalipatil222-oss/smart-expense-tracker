import io
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import current_user
from app.services.insight_service import InsightService
from app.services.forecast_service import ForecastService
from app.services.report_service import ReportService

insights_bp = Blueprint("insights", __name__)

@insights_bp.route("/")
def index():
    today = date.today()
    overview = InsightService.get_spending_overview(today)
    mom = InsightService.compare_month_over_month(today)
    recommendations = InsightService.generate_recommendations(today)
    history = InsightService.get_monthly_history(months=6)
    forecast = ForecastService.generate_30d_forecast(today)

    # Calculate aggregate potential savings
    total_potential_savings = sum(r.get("potential_savings", 0.0) for r in recommendations)

    return render_template(
        "insights.html",
        overview=overview,
        mom=mom,
        recommendations=recommendations,
        total_potential_savings=round(total_potential_savings, 2),
        history=history,
        forecast=forecast,
    )

@insights_bp.route("/api/chart-data")
def chart_data():
    """
    JSON API returning historical trends and category distribution for interactive Chart.js widgets.
    """
    today = date.today()
    overview = InsightService.get_spending_overview(today)
    history = InsightService.get_monthly_history(months=6)
    mom = InsightService.compare_month_over_month(today)

    return jsonify({
        "history": history,
        "category_breakdown": overview["category_breakdown"],
        "mom_categories": mom["categories"][:8],
    })

@insights_bp.route("/api/forecast")
def api_forecast():
    """
    JSON API returning 30-day forward cash flow and projected balance simulation with 95% confidence bands.
    """
    today = date.today()
    forecast = ForecastService.generate_30d_forecast(today)
    return jsonify(forecast)

@insights_bp.route("/export/pdf")
def export_pdf():
    """
    Generates and downloads an Executive PDF Financial Statement & Tax Summary.
    Query params:
      period: 'month' (default), 'ytd', '90d', or 'custom'
      start_date: 'YYYY-MM-DD' (if custom)
      end_date: 'YYYY-MM-DD' (if custom)
    """
    today = date.today()
    period = request.args.get("period", "month").lower()

    if period == "ytd":
        start_date = date(today.year, 1, 1)
        end_date = today
    elif period == "90d":
        start_date = today - timedelta(days=90)
        end_date = today
    elif period == "custom":
        try:
            start_date = datetime.strptime(request.args.get("start_date", ""), "%Y-%m-%d").date()
            end_date = datetime.strptime(request.args.get("end_date", ""), "%Y-%m-%d").date()
        except ValueError:
            start_date = date(today.year, today.month, 1)
            end_date = today
    else:  # default 'month'
        start_date = date(today.year, today.month, 1)
        end_date = today

    user_name = "Guest User"
    if current_user and current_user.is_authenticated:
        user_name = current_user.username

    pdf_bytes = ReportService.generate_pdf_statement(
        start_date=start_date,
        end_date=end_date,
        user_name=user_name
    )

    filename = f"SmartExpense_Statement_{period}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

