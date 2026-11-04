from datetime import date, datetime, timedelta
from typing import List, Optional
from app.database import db
from app.models.goal import FinancialGoal, GoalContribution

class GoalService:
    """
    Financial Goal Tracking and Amortization Service.
    Enables setting savings targets, tracking real-time milestone progress,
    recording contributions, and computing required monthly savings velocity.
    """

    @classmethod
    def create_goal(
        cls,
        title: str,
        target_amount: float,
        target_date: date,
        current_amount: float = 0.0,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> FinancialGoal:
        """
        Creates a new financial savings target.
        """
        goal = FinancialGoal(
            title=title.strip(),
            description=description.strip() if description else None,
            target_amount=abs(float(target_amount)),
            current_amount=0.0,
            target_date=target_date,
            category_id=category_id,
            status="in_progress",
        )
        db.session.add(goal)
        db.session.commit()

        # If initial amount provided, log an initial contribution
        if current_amount > 0:
            cls.record_contribution(goal.id, current_amount, date.today(), "Initial balance")

        return goal

    @classmethod
    def record_contribution(
        cls,
        goal_id: int,
        amount: float,
        contribution_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> GoalContribution:
        """
        Adds funds toward a savings goal and checks for milestone completion.
        """
        goal = FinancialGoal.query.get_or_404(goal_id)
        if contribution_date is None:
            contribution_date = date.today()

        amount_val = float(amount)
        contribution = GoalContribution(
            goal_id=goal.id,
            amount=amount_val,
            date=contribution_date,
            notes=notes
        )
        db.session.add(contribution)

        # Update goal balance
        goal.current_amount = max(0.0, round(goal.current_amount + amount_val, 2))
        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"

        db.session.commit()
        return contribution

    @classmethod
    def get_goals_overview(cls) -> dict:
        """
        Calculates aggregate portfolio analytics for all financial goals.
        """
        goals = FinancialGoal.query.order_by(FinancialGoal.target_date).all()
        today = date.today()

        total_target = sum(g.target_amount for g in goals)
        total_saved = sum(g.current_amount for g in goals)
        total_remaining = sum(g.remaining_amount for g in goals)
        overall_progress = (total_saved / total_target * 100.0) if total_target > 0 else 0.0

        goals_data = []
        for g in goals:
            # Calculate required monthly savings velocity
            days_left = (g.target_date - today).days
            months_left = max(1.0, days_left / 30.4)
            monthly_required = (g.remaining_amount / months_left) if g.remaining_amount > 0 else 0.0

            goals_data.append({
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "remaining_amount": g.remaining_amount,
                "progress_percentage": g.progress_percentage,
                "target_date": g.target_date,
                "target_date_str": g.target_date.strftime("%b %d, %Y"),
                "days_remaining": days_left,
                "is_overdue": days_left < 0 and g.status != "completed",
                "monthly_required": round(monthly_required, 2),
                "status": g.status,
                "category_name": g.category.name if g.category else "General Savings",
                "contributions_count": g.contributions.count(),
            })

        return {
            "total_goals": len(goals),
            "completed_goals": sum(1 for g in goals if g.status == "completed"),
            "in_progress_goals": sum(1 for g in goals if g.status == "in_progress"),
            "total_target": round(total_target, 2),
            "total_saved": round(total_saved, 2),
            "total_remaining": round(total_remaining, 2),
            "overall_progress": round(overall_progress, 1),
            "goals": goals_data,
        }

    @classmethod
    def get_goal_trajectory(cls, goal_id: int) -> dict:
        """
        Extracts historical contribution progress to power visual chart rendering.
        """
        goal = FinancialGoal.query.get_or_404(goal_id)
        contributions = goal.contributions.order_by(GoalContribution.date).all()

        labels = [goal.created_at.strftime("%Y-%m-%d")]
        data_points = [0.0]

        cumulative = 0.0
        for c in contributions:
            cumulative += c.amount
            labels.append(c.date.strftime("%Y-%m-%d"))
            data_points.append(round(cumulative, 2))

        return {
            "title": goal.title,
            "target_amount": goal.target_amount,
            "labels": labels,
            "data": data_points,
        }
