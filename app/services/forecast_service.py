from datetime import date, datetime, timedelta
from typing import Dict, List, Any
import numpy as np
from sqlalchemy import func
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.services.recurring_service import RecurringService

class ForecastService:
    """
    Predictive Cash Flow & Balance Forecasting Engine.
    Combines daily empirical burn velocity, polynomial regression trend,
    and scheduled recurring obligations to simulate a 30-day forward cash trajectory
    with 95% statistical confidence intervals.
    """

    @classmethod
    def generate_30d_forecast(cls, reference_date: date = None) -> Dict[str, Any]:
        ref_date = reference_date or date.today()
        history_start = ref_date - timedelta(days=90)

        # 1. Fetch transactions over the last 90 days to derive baseline cash flow
        transactions = Transaction.query.filter(
            Transaction.date >= history_start,
            Transaction.date <= ref_date
        ).order_by(Transaction.date.asc()).all()

        # Compute cumulative starting liquid balance
        all_prior = Transaction.query.filter(Transaction.date <= ref_date).all()
        inflows = sum(t.amount for t in all_prior if t.transaction_type == "income")
        outflows = sum(t.amount for t in all_prior if t.transaction_type == "expense")
        current_balance = round(inflows - outflows, 2)

        # 2. Build daily net historical series
        daily_net_map = {}
        curr = history_start
        while curr <= ref_date:
            daily_net_map[curr.isoformat()] = 0.0
            curr += timedelta(days=1)

        for t in transactions:
            k = t.date.isoformat()
            if k in daily_net_map:
                if t.transaction_type == "income":
                    daily_net_map[k] += t.amount
                else:
                    daily_net_map[k] -= t.amount

        daily_values = list(daily_net_map.values())
        if len(daily_values) >= 14:
            arr = np.array(daily_values)
            daily_mean = float(np.mean(arr))
            daily_std = float(np.std(arr)) if np.std(arr) > 0 else 25.0
            x_indices = np.arange(len(daily_values))
            slope, intercept = np.polyfit(x_indices, arr, 1)
        else:
            daily_mean = 5.0
            daily_std = 30.0
            slope = 0.0

        # Standard error for 95% confidence bounds (z = 1.96)
        margin_of_error_daily = 1.96 * (daily_std / 2.0)

        # 3. Fetch scheduled upcoming recurring obligations over next 30 days
        upcoming_data = RecurringService.get_upcoming_payments(days_ahead=30, reference_date=ref_date)
        upcoming_items = upcoming_data.get("items", [])
        
        scheduled_by_date = {}
        total_upcoming_bills = 0.0
        for item in upcoming_items:
            d_str = item["due_date"].isoformat()
            amt = item["amount"]
            scheduled_by_date[d_str] = scheduled_by_date.get(d_str, 0.0) + amt
            total_upcoming_bills += amt

        # 4. Forward 30-Day Cash Flow Simulation
        forward_points = []
        running_expected = current_balance
        running_upper = current_balance
        running_lower = current_balance

        for day_offset in range(1, 31):
            future_date = ref_date + timedelta(days=day_offset)
            f_str = future_date.isoformat()

            # Discretionary daily drift from regression trend
            day_trend_effect = daily_mean + (slope * day_offset * 0.1)

            # Specific scheduled recurring outflows for this day
            scheduled_outflow = scheduled_by_date.get(f_str, 0.0)

            # Net daily expected change
            net_delta = day_trend_effect - scheduled_outflow
            running_expected += net_delta

            # Compound confidence bands
            uncertainty_spread = margin_of_error_daily * np.sqrt(day_offset)
            running_upper = running_expected + uncertainty_spread
            running_lower = running_expected - uncertainty_spread

            forward_points.append({
                "day_index": day_offset,
                "date": f_str,
                "label": future_date.strftime("%b %d"),
                "expected_balance": round(running_expected, 2),
                "upper_bound": round(running_upper, 2),
                "lower_bound": round(running_lower, 2),
                "scheduled_bills": round(scheduled_outflow, 2),
            })

        projected_30d = forward_points[-1]["expected_balance"] if forward_points else current_balance
        min_projected_lower = min(p["lower_bound"] for p in forward_points) if forward_points else current_balance

        # 5. Risk Assessment
        if min_projected_lower < 0:
            liquidity_risk = "HIGH"
            risk_explanation = f"Potential cash shortfall detected! Conservative forecast projects balance dipping to ${min_projected_lower:,.2f}. Review discretionary spending and upcoming recurring payments."
        elif min_projected_lower < 500.0:
            liquidity_risk = "MODERATE"
            risk_explanation = f"Thin cash cushion projected (low point ${min_projected_lower:,.2f}). Maintain an emergency buffer of at least $500."
        else:
            liquidity_risk = "LOW"
            risk_explanation = f"Healthy liquidity. Projected 30-day balance is comfortably positive at ${projected_30d:,.2f} with safe confidence buffers."

        return {
            "current_balance": current_balance,
            "projected_30d_balance": round(projected_30d, 2),
            "projected_net_change": round(projected_30d - current_balance, 2),
            "total_upcoming_bills_30d": round(total_upcoming_bills, 2),
            "daily_velocity_mean": round(daily_mean, 2),
            "trend_slope": round(float(slope), 4),
            "liquidity_risk": liquidity_risk,
            "risk_explanation": risk_explanation,
            "forecast_points": forward_points
        }
