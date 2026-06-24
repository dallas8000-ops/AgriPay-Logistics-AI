from decimal import Decimal

from django.test import SimpleTestCase

from apps.payments.sms_parser import parse_mobile_money_sms


class SmsParserTests(SimpleTestCase):
    def test_mtn_received_with_reference(self):
        text = (
            "MTN Mobile Money: You have received UGX 50,000 from 256701234567. "
            "Transaction ID: 1234567890. Fee UGX 500. Ref AGR-12"
        )
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mtn_momo")
        self.assertEqual(parsed.amount, Decimal("50000"))
        self.assertEqual(parsed.currency, "UGX")
        self.assertEqual(parsed.order_reference, "AGR-12")
        self.assertGreater(parsed.confidence, 0.5)

    def test_mpesa_received(self):
        text = "MPESA confirmed You have received Ksh 1,200.00 from JOHN DOE 254712345678"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mpesa")
        self.assertEqual(parsed.amount, Decimal("1200"))
        self.assertEqual(parsed.currency, "KES")

    def test_airtel_payment(self):
        text = "Airtel Money: You have received TZS 25,000 from 255712345678. Txn 9876543210"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "airtel_money")
        self.assertEqual(parsed.amount, Decimal("25000"))

    def test_inv_reference(self):
        text = "MTN: received UGX 100,000 from 256700111222. Ref INV-5"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.order_reference, "INV-5")
