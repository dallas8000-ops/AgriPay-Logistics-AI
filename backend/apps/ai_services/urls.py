from django.urls import path

from .views import BuyerScoreView, MarketOverviewView, PriceEstimateView, RouteSummaryView

urlpatterns = [
    path("price-estimate/", PriceEstimateView.as_view(), name="price_estimate"),
    path("market-overview/", MarketOverviewView.as_view(), name="market_overview"),
    path("buyer-score/", BuyerScoreView.as_view(), name="buyer_score"),
    path("buyer-score/<int:buyer_id>/", BuyerScoreView.as_view(), name="buyer_score_detail"),
    path("route-summary/", RouteSummaryView.as_view(), name="route_summary"),
]
