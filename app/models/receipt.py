from datetime import datetime
from sqlalchemy import func
from app.database import db

class ReceiptScan(db.Model):
    __tablename__ = "receipt_scans"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    raw_text = db.Column(db.Text, nullable=True)
    
    # Extracted data
    extracted_merchant = db.Column(db.String(128), nullable=True)
    extracted_date = db.Column(db.Date, nullable=True)
    extracted_amount = db.Column(db.Float, nullable=True)
    confidence_score = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(24), default="pending_review", nullable=False)  # 'pending_review', 'confirmed', 'discarded'
    created_at = db.Column(db.DateTime, default=func.now())

    transactions = db.relationship("Transaction", back_populates="receipt_scan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "raw_text": self.raw_text,
            "extracted_merchant": self.extracted_merchant,
            "extracted_date": self.extracted_date.isoformat() if self.extracted_date else None,
            "extracted_amount": self.extracted_amount,
            "confidence_score": round(self.confidence_score, 2),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReceiptScan {self.filename} status={self.status}>"

