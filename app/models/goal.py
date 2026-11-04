from datetime import datetime, date
from sqlalchemy import func
from app.database import db

class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    status = db.Column(db.String(16), default="in_progress", nullable=False)  # 'in_progress', 'completed', 'paused'
    created_at = db.Column(db.DateTime, default=func.now())

    category = db.relationship("Category")
    contributions = db.relationship("GoalContribution", back_populates="goal", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def progress_percentage(self) -> float:
        if self.target_amount <= 0:
            return 100.0
        pct = (self.current_amount / self.target_amount) * 100.0
        return round(min(pct, 100.0), 1)

    @property
    def remaining_amount(self) -> float:
        return max(0.0, round(self.target_amount - self.current_amount, 2))

    @property
    def days_remaining(self) -> int:
        if not self.target_date:
            return 0
        delta = (self.target_date - date.today()).days
        return max(0, delta)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "remaining_amount": self.remaining_amount,
            "progress_percentage": self.progress_percentage,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "days_remaining": self.days_remaining,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "General Savings",
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<FinancialGoal {self.title}: ${self.current_amount}/${self.target_amount}>"


class GoalContribution(db.Model):
    __tablename__ = "goal_contributions"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("financial_goals.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    goal = db.relationship("FinancialGoal", back_populates="contributions")

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "amount": self.amount,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

