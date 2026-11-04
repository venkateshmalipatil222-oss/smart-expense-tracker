from datetime import date
from dateutil.relativedelta import relativedelta
from app.models.goal import FinancialGoal
from app.services.goal_service import GoalService

def test_goal_creation_and_progress(app):
    with app.app_context():
        today = date.today()
        deadline = today + relativedelta(months=6)

        goal = GoalService.create_goal(
            title="Emergency Fund",
            target_amount=1000.0,
            target_date=deadline,
            current_amount=250.0,
        )

        assert goal.target_amount == 1000.0
        assert goal.current_amount == 250.0
        assert goal.progress_percentage == 25.0
        assert goal.remaining_amount == 750.0
        assert goal.status == "in_progress"

        # Record contribution
        GoalService.record_contribution(goal.id, 750.0, today, "Final target contribution")

        refreshed = FinancialGoal.query.get(goal.id)
        assert refreshed.current_amount == 1000.0
        assert refreshed.progress_percentage == 100.0
        assert refreshed.remaining_amount == 0.0
        assert refreshed.status == "completed"

def test_goals_overview_analytics(app):
    with app.app_context():
        today = date.today()

        GoalService.create_goal(
            title="Vacation",
            target_amount=2000.0,
            target_date=today + relativedelta(months=4),
            current_amount=500.0,
        )

        overview = GoalService.get_goals_overview()
        assert overview["total_goals"] >= 1
        assert overview["total_target"] >= 2000.0
        assert overview["total_saved"] >= 500.0
        assert overview["total_remaining"] >= 1500.0
        assert overview["overall_progress"] > 0.0

