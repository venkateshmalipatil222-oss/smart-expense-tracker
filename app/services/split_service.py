from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from app.database import db
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.split import TransactionSplit, ExpenseShare

class SplitService:
    """
    Split & Expense Sharing Service.
    Handles itemized multi-category transaction splitting and group expense sharing (IOUs).
    """

    @classmethod
    def apply_itemized_splits(cls, transaction_id: int, splits_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Splits a single transaction across multiple categories.
        Validates that the sum of item amounts matches the transaction amount within 0.02 cents tolerance.
        """
        tx = db.session.get(Transaction, transaction_id)
        if not tx:
            raise ValueError(f"Transaction with ID {transaction_id} not found.")

        if not splits_data:
            raise ValueError("At least one split item must be specified.")

        total_split_amount = 0.0
        validated_items = []

        for idx, item in enumerate(splits_data):
            cat_id = item.get("category_id")
            amount = float(item.get("amount", 0.0))
            desc = (item.get("description") or "").strip()

            if amount <= 0:
                raise ValueError(f"Item #{idx+1} amount must be greater than zero.")

            cat = db.session.get(Category, cat_id)
            if not cat:
                raise ValueError(f"Category ID {cat_id} does not exist.")

            total_split_amount += amount
            validated_items.append({
                "category_id": cat_id,
                "amount": amount,
                "description": desc or tx.description
            })

        # Floating point tolerance check (within 2 cents)
        if abs(total_split_amount - tx.amount) > 0.02:
            diff = round(tx.amount - total_split_amount, 2)
            raise ValueError(
                f"Split amounts sum (${total_split_amount:,.2f}) does not match transaction total (${tx.amount:,.2f}). "
                f"Difference: ${diff:,.2f}"
            )

        # Remove previous splits for this transaction atomically
        TransactionSplit.query.filter_by(transaction_id=tx.id).delete()

        # Insert new splits
        new_splits = []
        for item in validated_items:
            split_record = TransactionSplit(
                transaction_id=tx.id,
                category_id=item["category_id"],
                amount=round(item["amount"], 2),
                description=item["description"]
            )
            db.session.add(split_record)
            new_splits.append(split_record)

        db.session.commit()

        return {
            "success": True,
            "transaction_id": tx.id,
            "total_splits": len(new_splits),
            "splits": [s.to_dict() for s in new_splits]
        }

    @classmethod
    def apply_expense_shares(cls, transaction_id: int, shares_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates or updates group expense sharing / IOU allocations for a transaction.
        Validates that total shared amounts do not exceed transaction total.
        """
        tx = db.session.get(Transaction, transaction_id)
        if not tx:
            raise ValueError(f"Transaction with ID {transaction_id} not found.")

        if not shares_data:
            # If empty array passed, clear existing shares
            ExpenseShare.query.filter_by(transaction_id=tx.id).delete()
            db.session.commit()
            return {"success": True, "transaction_id": tx.id, "shares": []}

        total_shares = 0.0
        validated_shares = []

        for idx, item in enumerate(shares_data):
            person = (item.get("person_name") or "").strip()
            amount = float(item.get("amount", 0.0))
            notes = (item.get("notes") or "").strip()

            if not person:
                raise ValueError(f"Share #{idx+1} is missing a person name.")

            if amount <= 0:
                raise ValueError(f"Share #{idx+1} for '{person}' must have an amount greater than 0.")

            total_shares += amount
            validated_shares.append({
                "person_name": person,
                "amount": round(amount, 2),
                "notes": notes
            })

        if total_shares > (tx.amount + 0.02):
            raise ValueError(
                f"Total shared amount (${total_shares:,.2f}) cannot exceed transaction amount (${tx.amount:,.2f})."
            )

        # Clear existing and insert updated shares
        ExpenseShare.query.filter_by(transaction_id=tx.id).delete()
        created_records = []
        for s in validated_shares:
            share = ExpenseShare(
                transaction_id=tx.id,
                person_name=s["person_name"],
                amount=s["amount"],
                notes=s["notes"],
                is_settled=False
            )
            db.session.add(share)
            created_records.append(share)

        db.session.commit()

        return {
            "success": True,
            "transaction_id": tx.id,
            "total_shares": len(created_records),
            "shares": [s.to_dict() for s in created_records]
        }

    @classmethod
    def settle_share(cls, share_id: int) -> Dict[str, Any]:
        """
        Marks an expense share / IOU as settled.
        """
        share = db.session.get(ExpenseShare, share_id)
        if not share:
            raise ValueError(f"Expense share with ID {share_id} not found.")

        share.is_settled = True
        share.settled_at = datetime.now()
        db.session.commit()

        return {
            "success": True,
            "share": share.to_dict()
        }

    @classmethod
    def unsettle_share(cls, share_id: int) -> Dict[str, Any]:
        """
        Reverts an expense share back to pending/unsettled.
        """
        share = db.session.get(ExpenseShare, share_id)
        if not share:
            raise ValueError(f"Expense share with ID {share_id} not found.")

        share.is_settled = False
        share.settled_at = None
        db.session.commit()

        return {
            "success": True,
            "share": share.to_dict()
        }

    @classmethod
    def get_sharing_summary(cls) -> Dict[str, Any]:
        """
        Aggregates pending IOUs, people balances, and overall group sharing telemetry.
        """
        all_shares = ExpenseShare.query.order_by(ExpenseShare.created_at.desc()).all()

        unsettled_shares = [s for s in all_shares if not s.is_settled]
        settled_shares = [s for s in all_shares if s.is_settled]

        total_unsettled = sum(s.amount for s in unsettled_shares)
        total_settled = sum(s.amount for s in settled_shares)

        # Group pending by person
        by_person: Dict[str, Dict[str, Any]] = {}
        for s in unsettled_shares:
            p = s.person_name
            if p not in by_person:
                by_person[p] = {
                    "person_name": p,
                    "total_owed": 0.0,
                    "unsettled_count": 0,
                    "shares": []
                }
            by_person[p]["total_owed"] += s.amount
            by_person[p]["unsettled_count"] += 1
            by_person[p]["shares"].append(s.to_dict())

        # Sort people by total owed desc
        sorted_people = sorted(by_person.values(), key=lambda x: x["total_owed"], reverse=True)
        for item in sorted_people:
            item["total_owed"] = round(item["total_owed"], 2)

        return {
            "total_unsettled_amount": round(total_unsettled, 2),
            "total_settled_amount": round(total_settled, 2),
            "pending_people_count": len(sorted_people),
            "balances_by_person": sorted_people,
            "all_shares": [s.to_dict() for s in all_shares],
            "unsettled_count": len(unsettled_shares),
            "settled_count": len(settled_shares),
        }
