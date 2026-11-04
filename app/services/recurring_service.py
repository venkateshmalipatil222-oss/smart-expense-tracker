from datetime import date, datetime, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta
from app.database import db
from app.models.recurring import RecurringRule
from app.models.transaction import Transaction
from app.services.anomaly_service import AnomalyDetectionService

class RecurringService:
    """
    Recurring Transactions Management & Scheduling Engine.
    Handles daily, weekly, monthly and yearly recurrence patterns, ensures idempotent
    execution with duplicate creation prevention, and projects upcoming cash commitments.
    """

    @staticmethod
    def calculate_next_due_date(current_due: date, frequency: str, interval: int = 1) -> date:
        """
        Advances the due date based on recurrence frequency and interval multiplier.
        """
        freq = frequency.lower()
        if freq == "daily":
            return current_due + timedelta(days=interval)
        elif freq == "weekly":
            return current_due + timedelta(weeks=interval)
        elif freq == "monthly":
            return current_due + relativedelta(months=interval)
        elif freq == "yearly":
            return current_due + relativedelta(years=interval)
        else:
            return current_due + relativedelta(months=interval)

    @classmethod
    def create_rule(
        cls,
        description: str,
        amount: float,
        category_id: int,
        frequency: str,
        start_date: date,
        interval: int = 1,
        end_date: Optional[date] = None,
        merchant: Optional[str] = None,
        transaction_type: str = "expense",
    ) -> RecurringRule:
        """
        Creates and schedules a new recurring rule.
        """
        rule = RecurringRule(
            description=description.strip(),
            merchant=merchant.strip() if merchant else None,
            amount=abs(float(amount)),
            transaction_type=transaction_type,
            category_id=category_id,
            frequency=frequency.lower(),
            interval=max(1, int(interval)),
            start_date=start_date,
            end_date=end_date,
            next_due_date=start_date,
            is_active=True,
        )
        db.session.add(rule)
        db.session.commit()
        return rule

    @classmethod
    def process_due_transactions(cls, as_of_date: Optional[date] = None) -> List[Transaction]:
        """
        Idempotently processes all active recurring schedules due on or before as_of_date.
        Strictly prevents duplicate transaction creation using database and date boundary checks.
        Advances next_due_date for each processed rule.
        """
        if as_of_date is None:
            as_of_date = date.today()

        due_rules = RecurringRule.query.filter(
            RecurringRule.is_active == True,
            RecurringRule.next_due_date <= as_of_date
        ).all()

        created_transactions = []

        for rule in due_rules:
            # Check if recurrence end date has passed
            if rule.end_date and rule.next_due_date > rule.end_date:
                rule.is_active = False
                continue

            current_due = rule.next_due_date

            # DUPLICATE PREVENTION CHECK:
            # 1. Has a transaction already been generated for this rule on this due date?
            existing_tx = Transaction.query.filter_by(
                recurring_rule_id=rule.id,
                date=current_due
            ).first()

            if not existing_tx:
                # 2. Check for identical amount, description, and date to prevent duplicate collisions
                collision = Transaction.query.filter_by(
                    description=rule.description,
                    amount=rule.amount,
                    date=current_due
                ).first()

                if not collision:
                    # Evaluate anomaly status
                    is_anom, score, reason, _ = AnomalyDetectionService.evaluate_transaction(
                        amount=rule.amount,
                        category_id=rule.category_id,
                        trans_date=current_due,
                        transaction_type=rule.transaction_type
                    )

                    new_tx = Transaction(
                        amount=rule.amount,
                        transaction_type=rule.transaction_type,
                        date=current_due,
                        description=rule.description,
                        merchant=rule.merchant,
                        category_id=rule.category_id,
                        recurring_rule_id=rule.id,
                        is_anomaly=is_anom,
                        anomaly_score=score,
                        anomaly_reason=reason,
                        notes=f"Auto-generated from recurring schedule '{rule.frequency.title()}'.",
                    )
                    db.session.add(new_tx)
                    created_transactions.append(new_tx)

            # Advance rule schedule
            rule.last_generated_date = current_due
            next_date = cls.calculate_next_due_date(current_due, rule.frequency, rule.interval)

            if rule.end_date and next_date > rule.end_date:
                rule.is_active = False
            else:
                rule.next_due_date = next_date

        db.session.commit()
        return created_transactions

    @classmethod
    def get_upcoming_payments(cls, days_ahead: int = 30, reference_date: date = None) -> dict:
        """
        Projects upcoming payments for all active recurring rules over the next N days.
        Returns ordered timeline and cash commitments summary.
        """
        today = reference_date or date.today()
        cutoff_date = today + timedelta(days=days_ahead)

        active_rules = RecurringRule.query.filter(RecurringRule.is_active == True).all()
        upcoming_items = []
        total_projected_expense = 0.0
        total_projected_income = 0.0

        for rule in active_rules:
            curr_due = rule.next_due_date

            # Simulate future occurrences up to cutoff_date
            while curr_due <= cutoff_date:
                if rule.end_date and curr_due > rule.end_date:
                    break

                days_until = (curr_due - today).days

                item = {
                    "rule_id": rule.id,
                    "description": rule.description,
                    "merchant": rule.merchant,
                    "amount": rule.amount,
                    "transaction_type": rule.transaction_type,
                    "category_name": rule.category.name if rule.category else "Uncategorized",
                    "category_icon": rule.category.icon if rule.category else "tag",
                    "category_color": rule.category.color if rule.category else "#6B7280",
                    "due_date": curr_due,
                    "due_date_str": curr_due.strftime("%b %d, %Y"),
                    "days_until": days_until,
                    "is_overdue": days_until < 0,
                    "is_today": days_until == 0,
                    "frequency": rule.frequency,
                }
                upcoming_items.append(item)

                if rule.transaction_type == "expense":
                    total_projected_expense += rule.amount
                else:
                    total_projected_income += rule.amount

                # Calculate next simulated occurrence
                curr_due = cls.calculate_next_due_date(curr_due, rule.frequency, rule.interval)
                if curr_due == rule.next_due_date:  # guard against infinite loops
                    break

        upcoming_items.sort(key=lambda x: x["due_date"])

        return {
            "timeframe_days": days_ahead,
            "upcoming_count": len(upcoming_items),
            "total_projected_expense": round(total_projected_expense, 2),
            "total_projected_income": round(total_projected_income, 2),
            "net_projected_outflow": round(total_projected_expense - total_projected_income, 2),
            "items": upcoming_items,
        }

