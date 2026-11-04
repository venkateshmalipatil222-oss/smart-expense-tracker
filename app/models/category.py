from datetime import datetime
from sqlalchemy import func
from app.database import db

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    icon = db.Column(db.String(32), default="tag")
    color = db.Column(db.String(16), default="#6B7280")
    is_income = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())

    transactions = db.relationship("Transaction", back_populates="category", lazy="dynamic")
    recurring_rules = db.relationship("RecurringRule", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "is_income": self.is_income,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Category {self.name}>"

