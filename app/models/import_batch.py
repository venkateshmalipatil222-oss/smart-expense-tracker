from datetime import datetime
from sqlalchemy import func
from app.database import db

class ImportBatch(db.Model):
    __tablename__ = "import_batches"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    total_rows = db.Column(db.Integer, default=0, nullable=False)
    imported_rows = db.Column(db.Integer, default=0, nullable=False)
    skipped_duplicates = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(24), default="completed", nullable=False)  # 'completed', 'failed', 'partial'
    created_at = db.Column(db.DateTime, default=func.now())

    transactions = db.relationship("Transaction", back_populates="import_batch", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "total_rows": self.total_rows,
            "imported_rows": self.imported_rows,
            "skipped_duplicates": self.skipped_duplicates,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ImportBatch {self.filename}: imported {self.imported_rows}/{self.total_rows}>"

