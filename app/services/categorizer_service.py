import re
from typing import Optional, Tuple
import numpy as np
from sqlalchemy import func
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from app.models.category import Category
from app.models.transaction import Transaction

class CategorizerService:
    """
    Hybrid Rule-Based and Machine Learning Expense Categorization Engine.
    Uses high-precision merchant dictionary matching alongside a TF-IDF Naive Bayes NLP model.
    Yields category suggestions with confidence ratings, alternative options, and method provenance.
    Never enforces predictions, allowing total user override.
    """

    # Comprehensive high-precision keyword dictionary for common merchants & narratives
    KEYWORD_RULES = {
        "Food & Dining": [
            "starbucks", "mcdonalds", "subway", "chipotle", "burger", "pizza", "restaurant",
            "cafe", "coffee", "diner", "bakery", "bistro", "taco", "kfc", "dominos", "sushi",
            "food", "grill", "doordash", "ubereats", "grubhub", "groceries", "supermarket",
            "trader joe", "whole foods", "safeway", "kroger", "costco wholesale"
        ],
        "Transportation": [
            "uber", "lyft", "taxi", "cab", "metro", "subway token", "bus fare", "train",
            "amtrak", "gas station", "chevron", "shell", "exxon", "bp gas", "mobil", "parking",
            "toll", "car wash", "auto repair", "oil change", "transit"
        ],
        "Utilities": [
            "electric", "electricity", "water bill", "power", "gas utility", "sewer", "trash",
            "internet", "wifi", "broadband", "comcast", "verizon", "att", "t-mobile", "utility"
        ],
        "Entertainment": [
            "netflix", "spotify", "hulu", "disney", "hbo", "cinema", "movie", "theater",
            "ticketmaster", "concert", "steam", "playstation", "xbox", "nintendo", "audible", "youtube premium"
        ],
        "Shopping": [
            "amazon", "walmart", "target", "ebay", "best buy", "clothing", "apparel", "zara",
            "h&m", "nike", "shoes", "electronics", "mall", "ikea", "home depot"
        ],
        "Healthcare": [
            "pharmacy", "cvs", "walgreens", "hospital", "clinic", "doctor", "dental", "dentist",
            "optometry", "vision", "medicine", "prescription", "health", "urgent care"
        ],
        "Housing": [
            "rent", "mortgage", "hoa fee", "property tax", "apartment", "lease", "home insurance"
        ],
        "Travel": [
            "airline", "flight", "delta", "united airlines", "american airlines", "hotel", "airbnb",
            "marriott", "hilton", "booking.com", "expedia", "car rental", "hertz"
        ],
        "Income": [
            "salary", "paycheck", "payroll", "dividend", "interest income", "deposit", "bonus",
            "freelance", "stripe payout", "upwork", "venmo cashout", "refund"
        ],
    }

    # Training corpus of annotated financial descriptions
    BASE_CORPUS = [
        ("Starbucks Store #4829 Seattle", "Food & Dining"),
        ("Chipotle Mexican Grill Online", "Food & Dining"),
        ("Safeway Supermarket Produce", "Food & Dining"),
        ("Whole Foods Market Organic", "Food & Dining"),
        ("McDonalds Drive Thru Lunch", "Food & Dining"),
        ("Uber Trip San Francisco CA", "Transportation"),
        ("Lyft Ride Downtown", "Transportation"),
        ("Chevron Fuel Station Pump 4", "Transportation"),
        ("Shell Oil Gas Fill Up", "Transportation"),
        ("BART Rapid Transit Ticket", "Transportation"),
        ("ConEdison Electric Power Bill", "Utilities"),
        ("City Water and Sewage Dept", "Utilities"),
        ("AT&T Wireless Monthly Bill", "Utilities"),
        ("Comcast Xfinity Internet", "Utilities"),
        ("Netflix Subscription Streaming", "Entertainment"),
        ("Spotify Premium Family Plan", "Entertainment"),
        ("AMC Theatres Cinema Popcorn", "Entertainment"),
        ("PlayStation Network Store", "Entertainment"),
        ("Amazon Marketplace Purchase Order", "Shopping"),
        ("Target Store Retail Clothing", "Shopping"),
        ("Best Buy Electronics Store", "Shopping"),
        ("Nike Factory Outlet Apparel", "Shopping"),
        ("CVS Pharmacy Prescription Refill", "Healthcare"),
        ("Walgreens Health & Wellness", "Healthcare"),
        ("Dental Clinic Consultation Fee", "Healthcare"),
        ("Monthly Apartment Rental Payment", "Housing"),
        ("Home Mortgage Escrow Transfer", "Housing"),
        ("Delta Air Lines Flight Ticket", "Travel"),
        ("Airbnb Reservation Brooklyn NY", "Travel"),
        ("Marriott Hotel Room Stay", "Travel"),
        ("Direct Deposit Employer Payroll", "Income"),
        ("Monthly Salary Credit", "Income"),
        ("Freelance Client Payment Invoice", "Income"),
    ]

    _ml_pipeline: Optional[Pipeline] = None

    @classmethod
    def _train_ml_pipeline(cls):
        """
        Initializes and fits a TF-IDF + Multinomial Naive Bayes classification pipeline.
        Augments the base corpus with existing database transactions if available.
        """
        descriptions = [item[0] for item in cls.BASE_CORPUS]
        labels = [item[1] for item in cls.BASE_CORPUS]

        # Augment with existing DB transactions if available
        try:
            db_txs = Transaction.query.join(Category).filter(
                Transaction.description.isnot(None),
                Transaction.description != ""
            ).all()
            for tx in db_txs:
                if tx.category and tx.category.name:
                    descriptions.append(tx.description)
                    labels.append(tx.category.name)
        except Exception:
            pass

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, max_features=1000)),
            ("clf", MultinomialNB(alpha=0.1))
        ])
        pipeline.fit(descriptions, labels)
        cls._ml_pipeline = pipeline

    @classmethod
    def suggest_category(cls, description: str, amount: float = 0.0) -> dict:
        """
        Determines the most probable category for a transaction description.
        Returns:
            - category_id
            - category_name
            - confidence (0.0 to 1.0)
            - method ("RULE_BASED", "MACHINE_LEARNING", or "DEFAULT")
            - alternatives (top other suggestions)
        """
        if not description or not description.strip():
            default_cat = Category.query.filter_by(name="Shopping").first() or Category.query.first()
            return {
                "category_id": default_cat.id if default_cat else None,
                "category_name": default_cat.name if default_cat else "General",
                "confidence": 0.20,
                "method": "DEFAULT",
                "alternatives": [],
            }

        desc_clean = description.lower().strip()

        # Tier 1: High-Precision Rule-Based Keyword Matcher
        for cat_name, keywords in cls.KEYWORD_RULES.items():
            for kw in keywords:
                # Word boundary match
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, desc_clean) or kw in desc_clean:
                    cat_obj = Category.query.filter(func.lower(Category.name) == cat_name.lower()).first()
                    if cat_obj:
                        return {
                            "category_id": cat_obj.id,
                            "category_name": cat_obj.name,
                            "confidence": 0.96,
                            "method": "RULE_BASED",
                            "alternatives": [],
                        }

        # Tier 2: NLP & Machine Learning Classifier
        if cls._ml_pipeline is None:
            cls._train_ml_pipeline()

        try:
            probs = cls._ml_pipeline.predict_proba([desc_clean])[0]
            classes = cls._ml_pipeline.classes_
            sorted_indices = np.argsort(probs)[::-1]

            top_class = classes[sorted_indices[0]]
            top_prob = float(probs[sorted_indices[0]])

            # Build alternatives
            alternatives = []
            for idx in sorted_indices[1:4]:
                alt_class = classes[idx]
                alt_prob = float(probs[idx])
                if alt_prob > 0.05:
                    alternatives.append({"category": alt_class, "confidence": round(alt_prob, 2)})

            cat_obj = Category.query.filter(func.lower(Category.name) == top_class.lower()).first()
            if cat_obj and top_prob >= 0.30:
                return {
                    "category_id": cat_obj.id,
                    "category_name": cat_obj.name,
                    "confidence": round(top_prob, 2),
                    "method": "MACHINE_LEARNING",
                    "alternatives": alternatives,
                }
        except Exception:
            pass

        # Tier 3: Sensible Fallback
        fallback_cat = Category.query.filter(Category.name.in_(["Shopping", "Food & Dining", "Miscellaneous"])).first() or Category.query.first()
        return {
            "category_id": fallback_cat.id if fallback_cat else None,
            "category_name": fallback_cat.name if fallback_cat else "Uncategorized",
            "confidence": 0.30,
            "method": "DEFAULT",
            "alternatives": [],
        }
