from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai_services.market_data.crops import get_crop_quote, list_supported_countries
from apps.ai_services.pricing import estimate_price


class MultinationalPricingTests(SimpleTestCase):
    def test_supported_countries(self):
        countries = list_supported_countries()
        self.assertEqual(set(countries), {"UG", "KE", "TZ", "RW"})

    def test_uganda_maize_quote(self):
        quote = get_crop_quote("maize", "UG")
        self.assertIsNotNone(quote)
        self.assertEqual(quote["currency"], "UGX")
        self.assertGreater(quote["unit_price_local"], Decimal("1000"))

    @patch("apps.ai_services.pricing.get_fx_for_country")
    def test_live_market_estimate_uses_local_wholesale(self, mock_fx):
        mock_fx.return_value = {
            "rate": 3640.0,
            "base": "USD",
            "quote": "UGX",
            "updated_at": "Wed, 24 Jun 2026 00:02:32 +0000",
            "live": True,
        }
        result = estimate_price("maize", "UG", 500, "long_rains")
        self.assertEqual(result["method"], "live_market")
        self.assertEqual(result["currency"], "UGX")
        self.assertIsNotNone(result["market"])
        self.assertEqual(result["market"]["name"], "Biira millers market")
        self.assertGreater(result["unit_price"], 1000)

    @patch("apps.ai_services.pricing.get_crop_quote", return_value=None)
    @patch("apps.ai_services.pricing.get_fx_for_country")
    def test_fx_adjusted_when_no_local_quote(self, mock_fx, _mock_quote):
        mock_fx.return_value = {
            "rate": 130.0,
            "base": "USD",
            "quote": "KES",
            "updated_at": None,
            "live": True,
        }
        result = estimate_price("avocado", "KE", 100, "dry")
        self.assertEqual(result["method"], "fx_adjusted")
        self.assertIsNone(result["market"])
