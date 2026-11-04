import re
from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy import func
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.models.goal import FinancialGoal
from app.services.forecast_service import ForecastService

class CopilotService:
    """
    AI Financial Copilot & Natural Language Query Engine.
    Parses conversational queries into structured ledger operations,
    evaluates affordability, and provides data-backed financial intelligence.
    """

    @classmethod
    def process_query(cls, query_text: str, reference_date: date = None) -> Dict[str, Any]:
        ref_date = reference_date or date.today()
        q = (query_text or "").strip().lower()

        if not q:
            return cls._fallback_response()

        # 1. Check for Affordability Intent
        afford_match = re.search(r"(?:can i afford|affordability of|can i buy|should i buy)\s+(?:a|an|the)?\s*([a-zA-Z\s]+)?\$?([0-9,.]+)", q)
        if not afford_match:
            afford_match = re.search(r"\$?([0-9,.]+)\s*(?:can i afford|is affordable)", q)
            if afford_match:
                amount_str = afford_match.group(1).replace(",", "")
                item_desc = "purchase"
            else:
                amount_str = None
                item_desc = None
        else:
            item_desc = (afford_match.group(1) or "purchase").strip()
            amount_str = afford_match.group(2).replace(",", "")

        if amount_str:
            try:
                purchase_amount = abs(float(amount_str))
                if purchase_amount > 0:
                    return cls._handle_affordability(purchase_amount, item_desc, ref_date)
            except ValueError:
                pass

        # 2. Check for Recurring Subscriptions / Bills Intent
        if any(term in q for term in ["subscription", "recurring", "monthly bill", "fixed bill", "upcoming payment"]):
            return cls._handle_recurring_audit(ref_date)

        # 3. Check for Anomalies / Unusual Transactions Intent
        if any(term in q for term in ["unusual", "anomaly", "anomalies", "spike", "flagged", "strange"]):
            return cls._handle_anomaly_audit(ref_date)

        # 4. Check for Savings Goals Intent
        if any(term in q for term in ["goal", "emergency fund", "savings target", "vacation fund", "saving progress"]):
            return cls._handle_goals_audit()

        # 5. Check for Specific Category Spending
        categories = Category.query.all()
        for cat in categories:
            cat_name_clean = cat.name.lower()
            tokens = [t for t in re.split(r"[\s&]+", cat_name_clean) if len(t) > 3]
            if cat_name_clean in q or any(t in q for t in tokens):
                return cls._handle_category_spending(cat, ref_date)

        # 6. Check for Specific Merchant Spending
        merchant_match = re.search(r"(?:at|from|with|for)\s+([a-zA-Z0-9\s]+)", q)
        if merchant_match:
            cand = merchant_match.group(1).strip()
            if cand and not any(cand in cat.name.lower() for cat in categories):
                res = cls._handle_merchant_spending(cand, ref_date)
                if res:
                    return res

        # 7. Check for General Spending Overview / Financial Health
        if any(term in q for term in ["overview", "summary", "how am i doing", "financial health", "spending summary", "how much did i spend"]):
            return cls._handle_general_summary(ref_date)

        return cls._fallback_response()

    @classmethod
    def _handle_affordability(cls, amount: float, item_name: str, ref_date: date) -> Dict[str, Any]:
        forecast = ForecastService.generate_30d_forecast(ref_date)
        current_balance = forecast["current_balance"]
        projected_30d = forecast["projected_30d_balance"]
        upcoming_bills = forecast["total_upcoming_bills_30d"]
        safety_cushion = 500.0

        net_after_purchase = current_balance - amount
        projected_after_purchase = projected_30d - amount

        if net_after_purchase < 0:
            status = "NOT_RECOMMENDED"
            badge_color = "rose"
            verdict = f"High Risk: Insufficient Funds"
            explanation = (
                f"A purchase of **${amount:,.2f}** for *{item_name}* exceeds your current liquid balance of **${current_balance:,.2f}**, "
                f"putting you into an immediate overdraft of **${abs(net_after_purchase):,.2f}**. This is not recommended."
            )
        elif projected_after_purchase < safety_cushion:
            status = "CAUTION"
            badge_color = "amber"
            verdict = f"Caution: Tight Cash Flow"
            explanation = (
                f"You can physically afford **${amount:,.2f}** right now (balance drops from **${current_balance:,.2f}** to **${net_after_purchase:,.2f}**). "
                f"However, with **${upcoming_bills:,.2f}** in scheduled recurring bills due over the next 30 days, your projected buffer will dip to **${projected_after_purchase:,.2f}**, "
                f"which is below your recommended safety cushion of **${safety_cushion:,.2f}**."
            )
        else:
            status = "APPROVED"
            badge_color = "emerald"
            verdict = f"Safe: Purchase is Affordable"
            explanation = (
                f"Yes, this purchase is affordable! Your liquid balance will be **${net_after_purchase:,.2f}**, and even after accounting for "
                f"**${upcoming_bills:,.2f}** in upcoming bills, your expected 30-day balance remains healthy at **${projected_after_purchase:,.2f}**."
            )

        return {
            "intent": "AFFORDABILITY_CHECK",
            "reply": explanation,
            "verdict": verdict,
            "status": status,
            "badge_color": badge_color,
            "data": {
                "amount": amount,
                "current_balance": current_balance,
                "balance_after_purchase": round(net_after_purchase, 2),
                "upcoming_bills_30d": upcoming_bills,
                "projected_balance_after": round(projected_after_purchase, 2),
            },
            "suggestions": [
                "What are my upcoming bills?",
                "How much did I spend this month?",
                "Show my savings goals progress"
            ]
        }

    @classmethod
    def _handle_category_spending(cls, category: Category, ref_date: date) -> Dict[str, Any]:
        start_date = ref_date - timedelta(days=30)
        txs = Transaction.query.filter(
            Transaction.category_id == category.id,
            Transaction.date >= start_date,
            Transaction.date <= ref_date,
            Transaction.transaction_type == "expense"
        ).order_by(Transaction.amount.desc()).all()

        total = sum(t.amount for t in txs)
        count = len(txs)
        top_merchants = [t.merchant or t.description for t in txs[:3]]

        reply = (
            f"In the last 30 days, you spent **${total:,.2f}** across **{count} transactions** in **{category.name}**. "
        )
        if top_merchants:
            reply += f"Top expenditures include: *{', '.join(top_merchants)}*."

        return {
            "intent": "SPENDING_BY_CATEGORY",
            "reply": reply,
            "data": {
                "category_id": category.id,
                "category_name": category.name,
                "total_spent": round(total, 2),
                "transaction_count": count
            },
            "suggestions": [
                f"Can I afford a $100 purchase?",
                "What are my recurring subscriptions?",
                "Show unusual expenses"
            ]
        }

    @classmethod
    def _handle_merchant_spending(cls, merchant_name: str, ref_date: date) -> Dict[str, Any]:
        txs = Transaction.query.filter(
            (Transaction.merchant.ilike(f"%{merchant_name}%")) |
            (Transaction.description.ilike(f"%{merchant_name}%"))
        ).order_by(Transaction.date.desc()).all()

        if not txs:
            return None

        total = sum(t.amount for t in txs if t.transaction_type == "expense")
        count = len(txs)
        recent_date = txs[0].date.strftime("%b %d, %Y") if txs else "N/A"

        reply = (
            f"You have **{count} recorded transactions** matching **{merchant_name.title()}**, totaling **${total:,.2f}**. "
            f"Your most recent transaction was on {recent_date}."
        )

        return {
            "intent": "SPENDING_BY_MERCHANT",
            "reply": reply,
            "data": {
                "merchant": merchant_name,
                "total_spent": round(total, 2),
                "count": count
            },
            "suggestions": [
                "How much did I spend on Food & Dining?",
                "Can I afford a $250 purchase?",
                "Show monthly summary"
            ]
        }

    @classmethod
    def _handle_recurring_audit(cls, ref_date: date) -> Dict[str, Any]:
        rules = RecurringRule.query.filter(RecurringRule.is_active == True).all()
        total_monthly = sum(r.amount for r in rules if r.transaction_type == "expense")
        names = [f"**{r.description}** (${r.amount:,.2f})" for r in rules[:5]]

        reply = (
            f"You have **{len(rules)} active recurring commitments**, totaling approximately **${total_monthly:,.2f}/month** in fixed obligations. "
            f"Key items: {', '.join(names)}."
        )

        return {
            "intent": "RECURRING_AUDIT",
            "reply": reply,
            "data": {
                "active_count": len(rules),
                "monthly_commitment": round(total_monthly, 2)
            },
            "suggestions": [
                "Can I afford a $200 purchase?",
                "Any unusual expenses this month?",
                "Show my savings goals"
            ]
        }

    @classmethod
    def _handle_anomaly_audit(cls, ref_date: date) -> Dict[str, Any]:
        anomalies = Transaction.query.filter(
            Transaction.is_anomaly == True
        ).order_by(Transaction.date.desc()).limit(5).all()

        if not anomalies:
            reply = "Great news! No unusual or outlier transactions have been detected in your recent spending."
        else:
            items = [f"• **${a.amount:,.2f}** at *{a.merchant or a.description}* on {a.date.strftime('%b %d')} ({a.anomaly_reason or 'Statistical spike'})" for a in anomalies]
            reply = (
                f"We identified **{len(anomalies)} unusual expense transactions**:\n\n" + "\n".join(items)
            )

        return {
            "intent": "ANOMALY_SUMMARY",
            "reply": reply,
            "data": {"count": len(anomalies)},
            "suggestions": [
                "How much did I spend this month?",
                "Can I afford a $300 purchase?",
                "Show active subscriptions"
            ]
        }

    @classmethod
    def _handle_goals_audit(cls) -> Dict[str, Any]:
        goals = FinancialGoal.query.all()
        if not goals:
            reply = "You haven't set up any savings goals yet. Navigate to Savings Goals to create your first target!"
        else:
            lines = [f"• **{g.title}**: ${g.current_amount:,.2f} of ${g.target_amount:,.2f} ({g.progress_percentage:.1f}%)" for g in goals]
            reply = (
                f"Here is your savings goals progress:\n\n" + "\n".join(lines)
            )

        return {
            "intent": "SAVINGS_GOALS_STATUS",
            "reply": reply,
            "data": {"goals_count": len(goals)},
            "suggestions": [
                "Can I afford a $500 purchase?",
                "What are my recurring bills?",
                "Show overall financial summary"
            ]
        }

    @classmethod
    def _handle_general_summary(cls, ref_date: date) -> Dict[str, Any]:
        start_of_month = date(ref_date.year, ref_date.month, 1)
        txs = Transaction.query.filter(Transaction.date >= start_of_month, Transaction.date <= ref_date).all()
        inflow = sum(t.amount for t in txs if t.transaction_type == "income")
        outflow = sum(t.amount for t in txs if t.transaction_type == "expense")
        net = inflow - outflow
        savings_rate = (net / inflow * 100.0) if inflow > 0 else 0.0

        reply = (
            f"Here is your financial snapshot for **{ref_date.strftime('%B %Y')}**:\n\n"
            f"• **Total Income**: ${inflow:,.2f}\n"
            f"• **Total Expenses**: ${outflow:,.2f}\n"
            f"• **Net Savings**: ${net:,.2f} ({savings_rate:.1f}% savings rate)\n\n"
            f"Ask me about any specific category, merchant, or whether you can afford an upcoming purchase!"
        )

        return {
            "intent": "GENERAL_FINANCIAL_SUMMARY",
            "reply": reply,
            "data": {
                "inflow": round(inflow, 2),
                "outflow": round(outflow, 2),
                "net": round(net, 2),
                "savings_rate": round(savings_rate, 1)
            },
            "suggestions": [
                "Can I afford a $350 purchase?",
                "How much did I spend on Food & Dining?",
                "List recurring subscriptions"
            ]
        }

    @classmethod
    def _fallback_response(cls) -> Dict[str, Any]:
        reply = (
            "I'm your **SmartExpense Financial Copilot**! You can ask me:\n\n"
            "• **Affordability**: *'Can I afford a $450 weekend trip?'*\n"
            "• **Category Breakdown**: *'How much did I spend on Food & Dining?'*\n"
            "• **Merchant Audit**: *'How much have I spent at Starbucks?'*\n"
            "• **Subscriptions**: *'What are my recurring monthly bills?'*\n"
            "• **Outliers**: *'Any unusual expenses this month?'*\n"
            "• **Goals**: *'How is my savings goal progressing?'*"
        )
        return {
            "intent": "HELP_GUIDE",
            "reply": reply,
            "suggestions": [
                "Can I afford a $250 purchase?",
                "How much did I spend on Food & Dining?",
                "Show my active subscriptions",
                "Show monthly summary"
            ]
        }
