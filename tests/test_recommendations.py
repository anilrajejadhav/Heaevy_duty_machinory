"""Tests for frequently-bought-together recommendations."""

from app.recommendations.service import RecommendationService


def test_recommendations_count_pairs(tmp_path) -> None:
    purchases = tmp_path / "purchases.csv"
    purchases.write_text(
        "CustomerID,PurchasedArticles\n"
        '1,"REF 111TA2234,REF 147TA5071"\n'
        '2,"REF 111TA2234,REF 147TA5071"\n',
        encoding="utf-8",
    )
    service = RecommendationService()

    service.build_from_csv(purchases)

    recommendation = service.get("REF 111TA2234")[0]
    assert recommendation.reference_number == "REF 147TA5071"
    assert recommendation.co_purchase_count == 2
