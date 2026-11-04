from datetime import date
from flask import Blueprint, render_template, jsonify
from app.services.insight_service import InsightService

insights_bp = Blueprint("insights", __name__)

@insights_bp.route("/")
def index():
    today = date.today()
    overview = InsightService.get_spending_overview(today)
    mom = InsightService.compare_month_over_month(today)
    recommendations = InsightService.generate_recommendations(today)
    history = InsightService.get_monthly_history(months=6)

    # Calculate aggregate potential savings
    total_potential_savings = sum(r.get("potential_savings", 0.0) for r in recommendations)

    return render_template(
        "insights.html",
        overview=overview,
        mom=mom,
        recommendations=recommendations,
        total_potential_savings=round(total_potential_savings, 2),
        history=history,
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

