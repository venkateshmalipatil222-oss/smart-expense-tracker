from datetime import datetime
from sqlalchemy import func
from app.database import db

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(16), default="expense", nullable=False)  # 'expense' or 'income'
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False, index=True)
    merchant = db.Column(db.String(128), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    
    # Multi-Currency fields
    currency = db.Column(db.String(3), default="USD", nullable=False)
    exchange_rate = db.Column(db.Float, default=1.0, nullable=False)
    original_amount = db.Column(db.Float, nullable=True)

    # Anomaly Detection tracking
    is_anomaly = db.Column(db.Boolean, default=False, nullable=False, index=True)
    anomaly_score = db.Column(db.Float, nullable=True)
    anomaly_reason = db.Column(db.String(255), nullable=True)
    
    # Traceability links
    receipt_scan_id = db.Column(db.Integer, db.ForeignKey("receipt_scans.id"), nullable=True)
    recurring_rule_id = db.Column(db.Integer, db.ForeignKey("recurring_rules.id"), nullable=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("import_batches.id"), nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    category = db.relationship("Category", back_populates="transactions")
    receipt_scan = db.relationship("ReceiptScan", back_populates="transactions")
    recurring_rule = db.relationship("RecurringRule", back_populates="transactions")
    import_batch = db.relationship("ImportBatch", back_populates="transactions")
    splits = db.relationship("TransactionSplit", back_populates="transaction", cascade="all, delete-orphan", lazy="select")
    shares = db.relationship("ExpenseShare", back_populates="transaction", cascade="all, delete-orphan", lazy="select")

    @property
    def is_split(self) -> bool:
        return bool(self.splits and len(self.splits) > 0)

    @property
    def is_shared(self) -> bool:
        return bool(self.shares and len(self.shares) > 0)

    @property
    def unsettled_shares_total(self) -> float:
        return sum(s.amount for s in self.shares if not s.is_settled)

    @property
    def settled_shares_total(self) -> float:
        return sum(s.amount for s in self.shares if s.is_settled)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "merchant": self.merchant,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "category_icon": self.category.icon if self.category else "tag",
            "category_color": self.category.color if self.category else "#6B7280",
            "currency": self.currency,
            "exchange_rate": self.exchange_rate,
            "original_amount": self.original_amount,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "anomaly_reason": self.anomaly_reason,
            "receipt_scan_id": self.receipt_scan_id,
            "recurring_rule_id": self.recurring_rule_id,
            "import_batch_id": self.import_batch_id,
            "is_split": self.is_split,
            "splits": [s.to_dict() for s in self.splits] if self.splits else [],
            "is_shared": self.is_shared,
            "shares": [s.to_dict() for s in self.shares] if self.shares else [],
            "unsettled_shares_total": round(self.unsettled_shares_total, 2),
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Transaction {self.date} {self.amount} {self.description}>"

