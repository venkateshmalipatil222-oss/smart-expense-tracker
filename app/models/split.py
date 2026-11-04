from datetime import datetime
from sqlalchemy import func
from app.database import db

class TransactionSplit(db.Model):
    """
    Itemized Sub-Split of a single Master Transaction across multiple categories.
    E.g. A $100 supermarket receipt split into $70 Food & Dining and $30 Household Utilities.
    """
    __tablename__ = "transaction_splits"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    transaction = db.relationship("Transaction", back_populates="splits")
    category = db.relationship("Category")

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "category_icon": self.category.icon if self.category else "tag",
            "category_color": self.category.color if self.category else "#6B7280",
            "amount": round(self.amount, 2),
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<TransactionSplit tx_id={self.transaction_id} cat_id={self.category_id} amount={self.amount}>"


class ExpenseShare(db.Model):
    """
    Group Expense Sharing / IOU split of a Master Transaction across people.
    Tracks receivables owed to the account holder and their settlement state.
    """
    __tablename__ = "expense_shares"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    person_name = db.Column(db.String(100), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    is_settled = db.Column(db.Boolean, default=False, nullable=False, index=True)
    settled_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    transaction = db.relationship("Transaction", back_populates="shares")

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "transaction_description": self.transaction.description if self.transaction else "",
            "transaction_amount": self.transaction.amount if self.transaction else 0.0,
            "transaction_date": self.transaction.date.isoformat() if self.transaction and self.transaction.date else None,
            "person_name": self.person_name,
            "amount": round(self.amount, 2),
            "is_settled": self.is_settled,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ExpenseShare person='{self.person_name}' amount={self.amount} settled={self.is_settled}>"
