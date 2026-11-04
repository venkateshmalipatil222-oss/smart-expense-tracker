import os
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from app import create_app
from app.database import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.models.goal import FinancialGoal, GoalContribution
from app.services.anomaly_service import AnomalyDetectionService

def seed_database():
    app = create_app()
    with app.app_context():
        print("Clearing and creating database schema...")
        db.create_all()

        # 0. Seed Demo User
        demo_user = User.query.filter_by(username="demo_user").first()
        if not demo_user:
            demo_user = User(username="demo_user", email="demo@example.com")
            demo_user.set_password("Password123!")
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: demo_user / Password123!")
        else:
            print("Demo user already exists.")

        # 1. Seed Categories
        categories_data = [
            {"name": "Food & Dining", "icon": "utensils", "color": "#F59E0B", "is_income": False},
            {"name": "Transportation", "icon": "truck", "color": "#3B82F6", "is_income": False},
            {"name": "Utilities", "icon": "bolt", "color": "#10B981", "is_income": False},
            {"name": "Entertainment", "icon": "film", "color": "#8B5CF6", "is_income": False},
            {"name": "Shopping", "icon": "shopping-bag", "color": "#EC4899", "is_income": False},
            {"name": "Healthcare", "icon": "heart", "color": "#EF4444", "is_income": False},
            {"name": "Housing", "icon": "home", "color": "#6366F1", "is_income": False},
            {"name": "Travel", "icon": "globe", "color": "#06B6D4", "is_income": False},
            {"name": "Income", "icon": "cash", "color": "#059669", "is_income": True},
            {"name": "Miscellaneous", "icon": "tag", "color": "#6B7280", "is_income": False},
        ]

        cat_map = {}
        for cdata in categories_data:
            existing = Category.query.filter_by(name=cdata["name"]).first()
            if not existing:
                cat = Category(**cdata)
                db.session.add(cat)
                db.session.flush()
                cat_map[cdata["name"]] = cat
            else:
                cat_map[cdata["name"]] = existing

        db.session.commit()
        print(f"Categories verified: {len(cat_map)} categories available.")

        # Check if transactions already exist
        if Transaction.query.count() > 0:
            print(f"Database already contains {Transaction.query.count()} transactions. Skipping seed.")
            return

        today = date.today()
        # 2. Generate 3 Months of Historical Transactions
        sample_transactions = []

        # Previous 2 Months & Current Month
        for m_offset in range(2, -1, -1):
            m_date = today - relativedelta(months=m_offset)
            m_start = date(m_date.year, m_date.month, 1)

            # Income (Salary) on 1st
            sample_transactions.append({
                "amount": 4200.00,
                "transaction_type": "income",
                "date": m_start,
                "description": "TechCorp Payroll Direct Deposit",
                "merchant": "TechCorp Inc",
                "category": cat_map["Income"],
            })

            # Housing (Rent) on 2nd
            sample_transactions.append({
                "amount": 1450.00,
                "transaction_type": "expense",
                "date": m_start + timedelta(days=1),
                "description": "Apartment Monthly Lease Payment",
                "merchant": "Parkview Apartments",
                "category": cat_map["Housing"],
            })

            # Utilities on 5th
            sample_transactions.append({
                "amount": 125.40,
                "transaction_type": "expense",
                "date": m_start + timedelta(days=4),
                "description": "ConEdison Electric & Gas Utility",
                "merchant": "ConEdison",
                "category": cat_map["Utilities"],
            })

            # Internet on 8th
            sample_transactions.append({
                "amount": 69.99,
                "transaction_type": "expense",
                "date": m_start + timedelta(days=7),
                "description": "Xfinity Gigabit Broadband Internet",
                "merchant": "Comcast",
                "category": cat_map["Utilities"],
            })

            # Entertainment (Netflix & Spotify)
            sample_transactions.append({
                "amount": 19.99,
                "transaction_type": "expense",
                "date": m_start + timedelta(days=10),
                "description": "Netflix 4K Streaming Subscription",
                "merchant": "Netflix",
                "category": cat_map["Entertainment"],
            })
            sample_transactions.append({
                "amount": 10.99,
                "transaction_type": "expense",
                "date": m_start + timedelta(days=12),
                "description": "Spotify Premium Individual",
                "merchant": "Spotify",
                "category": cat_map["Entertainment"],
            })

            # Groceries & Food across the month
            for d in [3, 9, 15, 22, 27]:
                if m_start + timedelta(days=d) <= today:
                    sample_transactions.append({
                        "amount": 78.50 + (d * 1.5),
                        "transaction_type": "expense",
                        "date": m_start + timedelta(days=d),
                        "description": "Trader Joe's Supermarket Groceries",
                        "merchant": "Trader Joe's",
                        "category": cat_map["Food & Dining"],
                    })

            # Dining Out (Increase in current month to trigger MoM surge!)
            dining_base = 45.00 if m_offset > 0 else 95.00
            for d in [6, 14, 20, 25]:
                if m_start + timedelta(days=d) <= today:
                    sample_transactions.append({
                        "amount": dining_base + (d * 1.2),
                        "transaction_type": "expense",
                        "date": m_start + timedelta(days=d),
                        "description": "Dinner & Drinks Restaurant",
                        "merchant": "Chipotle & Local Grill",
                        "category": cat_map["Food & Dining"],
                    })

            # Transportation (Uber & Gas)
            for d in [4, 11, 18, 24]:
                if m_start + timedelta(days=d) <= today:
                    sample_transactions.append({
                        "amount": 32.50,
                        "transaction_type": "expense",
                        "date": m_start + timedelta(days=d),
                        "description": "Uber Ride Commute",
                        "merchant": "Uber",
                        "category": cat_map["Transportation"],
                    })

            # Typical Shopping
            for d in [8, 19]:
                if m_start + timedelta(days=d) <= today:
                    sample_transactions.append({
                        "amount": 54.00,
                        "transaction_type": "expense",
                        "date": m_start + timedelta(days=d),
                        "description": "Amazon Retail Essentials",
                        "merchant": "Amazon",
                        "category": cat_map["Shopping"],
                    })

        # Add 1 Clear High-Outlier Anomaly in Shopping in current month
        sample_transactions.append({
            "amount": 890.00,
            "transaction_type": "expense",
            "date": today - timedelta(days=3),
            "description": "Nordstrom Designer Leather Jacket",
            "merchant": "Nordstrom",
            "category": cat_map["Shopping"],
            "notes": "One-off luxury celebration purchase",
        })

        # Persist transactions
        for item in sample_transactions:
            tx = Transaction(
                amount=item["amount"],
                transaction_type=item["transaction_type"],
                date=item["date"],
                description=item["description"],
                merchant=item.get("merchant"),
                category_id=item["category"].id,
                notes=item.get("notes"),
            )
            db.session.add(tx)

        db.session.commit()
        print(f"Inserted {len(sample_transactions)} realistic baseline transactions.")

        # 3. Anomaly Evaluation
        flagged = AnomalyDetectionService.reevaluate_all_transactions()
        print(f"Anomaly Engine flagged {flagged} unusual transactions.")

        # 4. Recurring Rules
        recurring_rules = [
            {
                "description": "Netflix 4K Subscription",
                "merchant": "Netflix",
                "amount": 19.99,
                "category_id": cat_map["Entertainment"].id,
                "frequency": "monthly",
                "interval": 1,
                "start_date": today.replace(day=10),
                "next_due_date": today.replace(day=10) if today.day <= 10 else (today + relativedelta(months=1)).replace(day=10),
            },
            {
                "description": "Apartment Rental Lease",
                "merchant": "Parkview Apartments",
                "amount": 1450.00,
                "category_id": cat_map["Housing"].id,
                "frequency": "monthly",
                "interval": 1,
                "start_date": today.replace(day=1),
                "next_due_date": (today + relativedelta(months=1)).replace(day=1),
            },
            {
                "description": "Planet Fitness Gym Membership",
                "merchant": "Planet Fitness",
                "amount": 12.50,
                "category_id": cat_map["Healthcare"].id,
                "frequency": "weekly",
                "interval": 1,
                "start_date": today + timedelta(days=2),
                "next_due_date": today + timedelta(days=2),
            },
        ]

        for rdata in recurring_rules:
            rule = RecurringRule(**rdata, is_active=True)
            db.session.add(rule)

        # 5. Financial Goals
        g1 = FinancialGoal(
            title="Emergency Fund",
            description="6 months of living expenses safely preserved in high-yield account.",
            target_amount=8000.00,
            current_amount=4500.00,
            target_date=today + relativedelta(months=8),
            status="in_progress",
            category_id=cat_map["Miscellaneous"].id,
        )
        db.session.add(g1)
        db.session.flush()

        # Log contributions
        db.session.add(GoalContribution(goal_id=g1.id, amount=2000.0, date=today - timedelta(days=60), notes="Tax refund allocation"))
        db.session.add(GoalContribution(goal_id=g1.id, amount=1500.0, date=today - timedelta(days=30), notes="Monthly bonus deposit"))
        db.session.add(GoalContribution(goal_id=g1.id, amount=1000.0, date=today - timedelta(days=5), notes="Regular savings allocation"))

        g2 = FinancialGoal(
            title="Japan Trip 2027",
            description="Flights, boutique hotels, and dining in Tokyo & Kyoto.",
            target_amount=3500.00,
            current_amount=1200.00,
            target_date=today + relativedelta(months=12),
            status="in_progress",
            category_id=cat_map["Travel"].id,
        )
        db.session.add(g2)
        db.session.flush()
        db.session.add(GoalContribution(goal_id=g2.id, amount=1200.0, date=today - timedelta(days=20), notes="Initial vacation fund allocation"))

        db.session.commit()
        print("Seeded recurring rules and financial goals.")
        print("Database initialization and seed complete!")

if __name__ == "__main__":
    seed_database()

