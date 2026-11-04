import pytest
from datetime import date, timedelta
from app import create_app
from app.config import TestConfig
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.models.goal import FinancialGoal, GoalContribution

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        
        # Populate basic categories
        categories = [
            Category(name="Food & Dining", icon="utensils", color="#F59E0B"),
            Category(name="Transportation", icon="truck", color="#3B82F6"),
            Category(name="Utilities", icon="bolt", color="#10B981"),
            Category(name="Entertainment", icon="film", color="#8B5CF6"),
            Category(name="Shopping", icon="shopping-bag", color="#EC4899"),
            Category(name="Healthcare", icon="heart", color="#EF4444"),
            Category(name="Housing", icon="home", color="#6366F1"),
            Category(name="Income", icon="cash", color="#059669", is_income=True),
            Category(name="Miscellaneous", icon="tag", color="#6B7280"),
        ]
        db.session.add_all(categories)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

