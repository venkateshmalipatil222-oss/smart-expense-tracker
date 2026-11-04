from app.services.categorizer_service import CategorizerService

def test_rule_based_keyword_matching(app):
    with app.app_context():
        # Starbucks -> Food & Dining
        sug1 = CategorizerService.suggest_category("Starbucks Coffee #1042")
        assert sug1["category_name"] == "Food & Dining"
        assert sug1["method"] == "RULE_BASED"
        assert sug1["confidence"] >= 0.90

        # Uber -> Transportation
        sug2 = CategorizerService.suggest_category("Uber Trip SF downtown")
        assert sug2["category_name"] == "Transportation"
        assert sug2["method"] == "RULE_BASED"
        assert sug2["confidence"] >= 0.90

        # Netflix -> Entertainment
        sug3 = CategorizerService.suggest_category("Netflix Streaming subscription")
        assert sug3["category_name"] == "Entertainment"
        assert sug3["method"] == "RULE_BASED"

def test_ml_nlp_classification(app):
    with app.app_context():
        # Text without exact keyword in dictionary, but related semantics
        sug = CategorizerService.suggest_category("Chipotle Mexican Grill Online")
        assert sug["category_name"] == "Food & Dining"
        assert sug["confidence"] > 0.40

def test_fallback_on_unrecognized_text(app):
    with app.app_context():
        sug = CategorizerService.suggest_category("XYZ998877 RANDOM TOKEN")
        assert sug["category_name"] is not None
        # Confidence should be appropriately low so UI prompts user
        assert sug["confidence"] <= 0.60

