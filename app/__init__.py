import os
from flask import Flask, request, redirect, url_for
from flask_login import LoginManager, current_user
from app.config import Config
from app.database import db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    # Ensure vital directories exist
    os.makedirs(flask_app.config["DATA_DIR"], exist_ok=True)
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(flask_app)
    login_manager.init_app(flask_app)

    # Self-healing database schema verification
    with flask_app.app_context():
        try:
            db.create_all()
            from sqlalchemy import text
            with db.engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
                cols = [r[1] for r in res] if res else []
                if cols:
                    if "currency" not in cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN currency VARCHAR(3) DEFAULT 'USD' NOT NULL"))
                    if "exchange_rate" not in cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN exchange_rate FLOAT DEFAULT 1.0 NOT NULL"))
                    if "original_amount" not in cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN original_amount FLOAT"))
                    conn.commit()
        except Exception:
            pass

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.core import core_bp
    from app.routes.insights import insights_bp
    from app.routes.receipts import receipts_bp
    from app.routes.recurring import recurring_bp
    from app.routes.goals import goals_bp
    from app.routes.import_stmt import import_bp
    from app.routes.splits import splits_bp

    flask_app.register_blueprint(auth_bp, url_prefix="/auth")
    flask_app.register_blueprint(core_bp)
    flask_app.register_blueprint(insights_bp, url_prefix="/insights")
    flask_app.register_blueprint(receipts_bp, url_prefix="/receipts")
    flask_app.register_blueprint(recurring_bp, url_prefix="/recurring")
    flask_app.register_blueprint(goals_bp, url_prefix="/goals")
    flask_app.register_blueprint(import_bp, url_prefix="/import")
    flask_app.register_blueprint(splits_bp)

    # Global Access Control: Unauthenticated visitors see only the login page
    @flask_app.before_request
    def enforce_authentication():
        # Static files and auth endpoints are publicly accessible
        if request.endpoint and (request.endpoint.startswith("auth.") or request.endpoint == "static"):
            return
        # If disabled in test configuration
        if not flask_app.config.get("REQUIRE_LOGIN", True):
            return
        # Unauthenticated users are redirected directly to the login page
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url if request.method == "GET" else None))

    # Context processors for global template data
    @flask_app.context_processor
    def inject_global_data():
        from app.models.category import Category
        from app.models.recurring import RecurringRule
        from app.services.currency_service import CurrencyService
        from datetime import date
        try:
            categories = Category.query.order_by(Category.name).all()
            pending_recurring_count = RecurringRule.query.filter(
                RecurringRule.is_active == True,
                RecurringRule.next_due_date <= date.today()
            ).count()
        except Exception:
            categories = []
            pending_recurring_count = 0
        return {
            "all_categories": categories,
            "pending_recurring_count": pending_recurring_count,
            "supported_currencies": CurrencyService.get_supported_currencies(),
        }

    # Custom Jinja filters
    @flask_app.template_filter("currency")
    def currency_filter(amount):
        if amount is None:
            return "$0.00"
        return f"${float(amount):,.2f}"

    with flask_app.app_context():
        from app.models import User, Category, Transaction, RecurringRule, FinancialGoal, GoalContribution, ReceiptScan, ImportBatch
        db.create_all()

    return flask_app
