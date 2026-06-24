from decimal import Decimal

from django.test import SimpleTestCase

from apps.payments.sms_parser import parse_mobile_money_sms

# Samples approximate real provider SMS layouts; formats vary by country and app version.


class SmsParserTests(SimpleTestCase):
    def test_mtn_uganda_received_with_reference(self):
        text = (
            "MTN Mobile Money: You have received UGX 50,000 from 256701234567. "
            "Transaction ID: 1234567890. Fee UGX 500. Ref AGR-12"
        )
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mtn_momo")
        self.assertEqual(parsed.amount, Decimal("50000"))
        self.assertEqual(parsed.currency, "UGX")
        self.assertEqual(parsed.order_reference, "AGR-12")
        self.assertEqual(parsed.payer_phone, "256701234567")
        self.assertGreater(parsed.confidence, 0.5)

    def test_mtn_yello_format(self):
        text = (
            "Y'ello. UGX 75,000 has been received from 256772345678. "
            "Trans ID: 9988776655. Available balance: UGX 120,000."
        )
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mtn_momo")
        self.assertEqual(parsed.amount, Decimal("75000"))
        self.assertEqual(parsed.currency, "UGX")

    def test_mpesa_safaricom_confirmed(self):
        text = (
            "TLAA1234 Confirmed. Ksh1,200.00 received from 254712345678-JOHN DOE "
            "on 23/6/26 at 10:15 AM. New M-PESA balance is Ksh5,000.00."
        )
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mpesa")
        self.assertEqual(parsed.amount, Decimal("1200"))
        self.assertEqual(parsed.currency, "KES")
        self.assertEqual(parsed.txn_reference, "TLAA1234")

    def test_mpesa_you_have_received(self):
        text = "MPESA confirmed You have received Ksh 1,200.00 from JOHN DOE 254712345678"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "mpesa")
        self.assertEqual(parsed.amount, Decimal("1200"))

    def test_mpesa_not_triggered_by_generic_confirmed(self):
        text = "Your delivery order is confirmed. Thank you for shopping with us."
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "unknown")
        self.assertIsNone(parsed.amount)

    def test_airtel_tanzania(self):
        text = "Airtel Money: You have received TZS 25,000 from 255712345678. Txn 9876543210"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "airtel_money")
        self.assertEqual(parsed.amount, Decimal("25000"))
        self.assertEqual(parsed.currency, "TZS")

    def test_airtel_uganda_has_been_received(self):
        text = (
            "Dear Customer, UGX 20,000 has been received from 256701112233. "
            "Financial Transaction ID 4455667788. Airtel Money."
        )
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.provider, "airtel_money")
        self.assertEqual(parsed.amount, Decimal("20000"))
        self.assertEqual(parsed.currency, "UGX")

    def test_inv_reference(self):
        text = "MTN MoMo: received UGX 100,000 from 256700111222. Ref INV-5"
        parsed = parse_mobile_money_sms(text)
        self.assertEqual(parsed.order_reference, "INV-5")
        self.assertEqual(parsed.amount, Decimal("100000"))
