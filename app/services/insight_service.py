from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction

class InsightService:
    """
    AI-Powered and Statistical Financial Insights Engine.
    Analyzes actual transaction history, computes Month-over-Month (MoM) deltas,
    identifies spending patterns, and synthesizes personalized saving recommendations
    with transparent explanations of rule-based vs statistical derivations.
    """

    @staticmethod
    def get_spending_overview(target_date: date = None) -> dict:
        """
        Computes high-level financial metrics for the month of target_date (default: today).
        """
        if target_date is None:
            target_date = date.today()

        month_start = date(target_date.year, target_date.month, 1)
        next_month = month_start + relativedelta(months=1)
        month_end = next_month - timedelta(days=1)

        # Query transactions in the month
        txs = Transaction.query.filter(
            Transaction.date >= month_start,
            Transaction.date <= month_end
        ).all()

        total_income = sum(t.amount for t in txs if t.transaction_type == "income")
        total_expense = sum(t.amount for t in txs if t.transaction_type == "expense")
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

        # Category breakdown for expenses
        cat_map = {}
        for t in txs:
            if t.transaction_type == "expense":
                cname = t.category.name if t.category else "Uncategorized"
                ccolor = t.category.color if t.category else "#9CA3AF"
                cicon = t.category.icon if t.category else "tag"
                if cname not in cat_map:
                    cat_map[cname] = {
                        "category_name": cname,
                        "color": ccolor,
                        "icon": cicon,
                        "total": 0.0,
                        "count": 0,
                    }
                cat_map[cname]["total"] += t.amount
                cat_map[cname]["count"] += 1

        category_breakdown = list(cat_map.values())
        category_breakdown.sort(key=lambda x: x["total"], reverse=True)

        for item in category_breakdown:
            item["percentage"] = round((item["total"] / total_expense * 100.0), 1) if total_expense > 0 else 0.0
            item["total"] = round(item["total"], 2)

        highest_category = category_breakdown[0] if category_breakdown else None

        return {
            "period": month_start.strftime("%B %Y"),
            "month_start": month_start,
            "month_end": month_end,
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_savings": round(net_savings, 2),
            "savings_rate": round(savings_rate, 1),
            "highest_category": highest_category,
            "category_breakdown": category_breakdown,
            "transaction_count": len(txs),
        }

    @staticmethod
    def compare_month_over_month(target_date: date = None) -> dict:
        """
        Compares current month spending against previous month spending.
        Computes categorical differentials, growth rates, and shifts in spending.
        """
        if target_date is None:
            target_date = date.today()

        current_month_start = date(target_date.year, target_date.month, 1)
        prev_month_start = current_month_start - relativedelta(months=1)
        prev_month_end = current_month_start - timedelta(days=1)
        curr_month_end = (current_month_start + relativedelta(months=1)) - timedelta(days=1)

        curr_txs = Transaction.query.filter(
            Transaction.date >= current_month_start,
            Transaction.date <= curr_month_end,
            Transaction.transaction_type == "expense"
        ).all()

        prev_txs = Transaction.query.filter(
            Transaction.date >= prev_month_start,
            Transaction.date <= prev_month_end,
            Transaction.transaction_type == "expense"
        ).all()

        curr_total = sum(t.amount for t in curr_txs)
        prev_total = sum(t.amount for t in prev_txs)

        abs_change = curr_total - prev_total
        pct_change = ((abs_change / prev_total) * 100.0) if prev_total > 0 else (100.0 if curr_total > 0 else 0.0)

        # Categorical comparisons
        def aggregate_by_category(tx_list):
            res = {}
            for t in tx_list:
                cname = t.category.name if t.category else "Uncategorized"
                res[cname] = res.get(cname, 0.0) + t.amount
            return res

        curr_cats = aggregate_by_category(curr_txs)
        prev_cats = aggregate_by_category(prev_txs)

        all_cat_names = set(curr_cats.keys()).union(set(prev_cats.keys()))
        comparison_table = []

        for name in all_cat_names:
            c_amt = curr_cats.get(name, 0.0)
            p_amt = prev_cats.get(name, 0.0)
            diff = c_amt - p_amt
            if p_amt > 0:
                pct = (diff / p_amt) * 100.0
            else:
                pct = 100.0 if c_amt > 0 else 0.0

            if diff > 0:
                direction = "increased"
            elif diff < 0:
                direction = "decreased"
            else:
                direction = "unchanged"

            comparison_table.append({
                "category": name,
                "current_amount": round(c_amt, 2),
                "previous_amount": round(p_amt, 2),
                "difference": round(diff, 2),
                "percent_change": round(pct, 1),
                "direction": direction,
            })

        comparison_table.sort(key=lambda x: abs(x["difference"]), reverse=True)

        return {
            "current_month_label": current_month_start.strftime("%B %Y"),
            "previous_month_label": prev_month_start.strftime("%B %Y"),
            "current_total": round(curr_total, 2),
            "previous_total": round(prev_total, 2),
            "difference": round(abs_change, 2),
            "percent_change": round(pct_change, 1),
            "direction": "increased" if abs_change > 0 else ("decreased" if abs_change < 0 else "steady"),
            "categories": comparison_table,
        }

    @staticmethod
    def get_monthly_history(months: int = 6) -> list:
        """
        Fetches historical total income and total expense for the last N calendar months.
        Used for trend charts and velocity detection.
        """
        today = date.today()
        history = []

        for i in range(months - 1, -1, -1):
            m_start = date(today.year, today.month, 1) - relativedelta(months=i)
            m_end = (m_start + relativedelta(months=1)) - timedelta(days=1)

            txs = Transaction.query.filter(
                Transaction.date >= m_start,
                Transaction.date <= m_end
            ).all()

            income = sum(t.amount for t in txs if t.transaction_type == "income")
            expense = sum(t.amount for t in txs if t.transaction_type == "expense")

            history.append({
                "month_label": m_start.strftime("%b %Y"),
                "month_key": m_start.strftime("%Y-%m"),
                "income": round(income, 2),
                "expense": round(expense, 2),
                "savings": round(income - expense, 2),
            })

        return history

    @classmethod
    def generate_recommendations(cls, target_date: date = None) -> list:
        """
        Synthesizes personalized saving suggestions using actual transaction data.
        Explicitly distinguishes RULE_BASED calculations from STATISTICAL_ML predictions.
        Provides transparent rationale and potential monthly savings estimates.
        """
        if target_date is None:
            target_date = date.today()

        overview = cls.get_spending_overview(target_date)
        mom = cls.compare_month_over_month(target_date)
        recommendations = []

        total_expense = overview["total_expense"]
        total_income = overview["total_income"]

        if total_expense == 0:
            return [{
                "title": "Build Your Baseline",
                "category": "General",
                "type": "RULE_BASED",
                "priority": "low",
                "potential_savings": 0.0,
                "suggestion": "No expenses logged this month yet. Continue recording transactions to unlock deep personalized insights.",
                "rationale": "Insights require actual transaction records to calculate category variances and historical baselines.",
            }]

        # 1. MoM Surge Recommendation (Statistical Analysis)
        for cat in mom["categories"]:
            if cat["current_amount"] > 100.0 and cat["percent_change"] >= 25.0:
                potential = round(cat["difference"] * 0.5, 2)
                recommendations.append({
                    "title": f"Spike in {cat['category']} Spending",
                    "category": cat["category"],
                    "type": "STATISTICAL_ML",
                    "priority": "high" if cat["percent_change"] >= 50 else "medium",
                    "potential_savings": potential,
                    "suggestion": (
                        f"Your {cat['category']} expenses surged by {cat['percent_change']}% "
                        f"(${cat['current_amount']} vs ${cat['previous_amount']} last month). "
                        f"Bringing this back toward your previous baseline could preserve ~${potential}/month."
                    ),
                    "rationale": (
                        f"Statistical MoM variance check flagged {cat['category']} with a +{cat['percent_change']}% "
                        f"deviation ($+{cat['difference']}) against the preceding 30-day window."
                    ),
                })
                break  # Top surge only to avoid overload

        # 2. Dominant Discretionary Category Analysis (Rule-Based 50/30/20 benchmark)
        discretionary_keywords = ["dining", "food", "entertainment", "shopping", "leisure", "travel"]
        for cat in overview["category_breakdown"]:
            cname_lower = cat["category_name"].lower()
            if any(k in cname_lower for k in discretionary_keywords):
                pct = cat["percentage"]
                if pct >= 20.0 and cat["total"] > 150.0:
                    potential = round(cat["total"] * 0.20, 2)
                    recommendations.append({
                        "title": f"Optimize Discretionary {cat['category_name']}",
                        "category": cat["category_name"],
                        "type": "RULE_BASED",
                        "priority": "high" if pct >= 30 else "medium",
                        "potential_savings": potential,
                        "suggestion": (
                            f"{cat['category_name']} accounts for {pct}% of your total monthly expenditures (${cat['total']}). "
                            f"Applying a modest 20% budget constraint could free up ${potential} for your savings goals."
                        ),
                        "rationale": (
                            f"Rule-Based Budget Allocation rule flags when any single discretionary category absorbs "
                            f">20% of aggregate monthly outflow. Current share: {pct}%."
                        ),
                    })
                    break

        # 3. High-Frequency Micro-Transactions Creep (Statistical Pattern)
        start_m = overview["month_start"]
        end_m = overview["month_end"]
        small_txs = Transaction.query.filter(
            Transaction.date >= start_m,
            Transaction.date <= end_m,
            Transaction.transaction_type == "expense",
            Transaction.amount <= 15.0
        ).all()

        if len(small_txs) >= 8:
            small_sum = sum(t.amount for t in small_txs)
            potential = round(small_sum * 0.35, 2)
            recommendations.append({
                "title": "Micro-Transaction Accumulation",
                "category": "Micro-Expenses",
                "type": "STATISTICAL_ML",
                "priority": "medium",
                "potential_savings": potential,
                "suggestion": (
                    f"You have {len(small_txs)} micro-transactions (under $15) totaling ${small_sum:.2f} this month. "
                    f"Consolidating frequent small purchases or cutting non-essential daily items could save ~${potential}/month."
                ),
                "rationale": (
                    f"Statistical frequency detection identified {len(small_txs)} micro-transactions totaling ${small_sum:.2f}, "
                    f"which subtly erodes disposable income without conscious tracking."
                ),
            })

        # 4. Savings Rate Benchmark (Rule-Based 20% Goal)
        if total_income > 0:
            curr_rate = overview["savings_rate"]
            if curr_rate < 15.0:
                shortfall = round((total_income * 0.20) - overview["net_savings"], 2)
                recommendations.append({
                    "title": "Savings Rate Below 20% Target",
                    "category": "General",
                    "type": "RULE_BASED",
                    "priority": "high",
                    "potential_savings": max(0.0, shortfall),
                    "suggestion": (
                        f"Your current net savings rate is {curr_rate}%. To reach the standard 20% financial wellness target, "
                        f"aim to save an additional ${max(0.0, shortfall):,.2f} this month."
                    ),
                    "rationale": (
                        f"Standard 50/30/20 Rule targets a minimum 20% net savings margin from gross income. "
                        f"Current margin is {curr_rate}% (${overview['net_savings']} out of ${total_income})."
                    ),
                })

        return recommendations

