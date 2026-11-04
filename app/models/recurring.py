from datetime import datetime
from sqlalchemy import func
from app.database import db

class RecurringRule(db.Model):
    __tablename__ = "recurring_rules"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    merchant = db.Column(db.String(128), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(16), default="expense", nullable=False)  # 'expense' or 'income'
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    
    # Recurrence configuration
    frequency = db.Column(db.String(16), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    interval = db.Column(db.Integer, default=1, nullable=False)  # every N days/weeks/months
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    
    # Schedule and execution state
    next_due_date = db.Column(db.Date, nullable=False, index=True)
    last_generated_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=func.now())

    category = db.relationship("Category", back_populates="recurring_rules")
    transactions = db.relationship("Transaction", back_populates="recurring_rule", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "merchant": self.merchant,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "category_icon": self.category.icon if self.category else "tag",
            "frequency": self.frequency,
            "interval": self.interval,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "next_due_date": self.next_due_date.isoformat() if self.next_due_date else None,
            "last_generated_date": self.last_generated_date.isoformat() if self.last_generated_date else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<RecurringRule {self.frequency} - {self.description} (${self.amount})>"

