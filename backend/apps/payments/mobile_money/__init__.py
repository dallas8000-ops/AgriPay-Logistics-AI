from apps.payments.models import Payment

from .airtel import AirtelMoneyClient, AirtelMoneyError
from .mpesa import MPesaClient, MPesaError
from .mtn import MTNMoMoClient, MTNMoMoError
from .utils import COUNTRY_DIAL_CODES, normalize_msisdn


class MobileMoneyService:
    """
    Mobile money orchestration.

    When provider API credentials are configured, calls the real sandbox/production APIs.
    Otherwise returns an explicit simulated flow (no fake USSD claims).
    """

    @staticmethod
    def provider_modes() -> dict[str, str]:
        return {
            Payment.Provider.MTN_MOMO: (
                "live" if MTNMoMoClient().is_configured() else "simulated"
            ),
            Payment.Provider.AIRTEL_MONEY: (
                "live" if AirtelMoneyClient().is_configured() else "simulated"
            ),
            Payment.Provider.MPESA: (
                "live" if MPesaClient().is_configured() else "simulated"
            ),
        }

    @staticmethod
    def _simulated_result(payment, provider: str, phone: str) -> dict:
        reference = f"SIM-{payment.id.hex[:12].upper()}"
        payment.external_reference = reference
        payment.status = Payment.Status.PROCESSING
        payment.phone_number = phone
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "simulated",
            "provider": provider,
        }
        payment.save()
        return {
            "reference": reference,
            "status": "processing",
            "integration_mode": "simulated",
            "provider": provider,
            "message": (
                "Simulated payment — no USSD/STK prompt was sent. "
                "Add provider API credentials to backend/.env for live sandbox integration."
            ),
            "requires_manual_confirm": True,
        }

    @staticmethod
    def initiate_mtn_payment(payment, phone: str) -> dict:
        client = MTNMoMoClient()
        dial = COUNTRY_DIAL_CODES.get(payment.payer.country, "256")
        msisdn = normalize_msisdn(phone, dial)

        if not client.is_configured():
            return MobileMoneyService._simulated_result(payment, Payment.Provider.MTN_MOMO, msisdn)

        reference_id = client.new_reference_id()
        try:
            client.request_to_pay(
                reference_id=reference_id,
                amount=str(int(payment.amount)) if payment.amount == int(payment.amount) else str(payment.amount),
                currency=payment.currency,
                phone=msisdn,
                external_id=str(payment.id),
                payer_message=f"AgriPay order {payment.order_id}",
                payee_note="AgriPay Logistics",
            )
        except MTNMoMoError as exc:
            payment.status = Payment.Status.FAILED
            payment.metadata = {**(payment.metadata or {}), "error": str(exc)}
            payment.save()
            raise

        payment.external_reference = reference_id
        payment.status = Payment.Status.PROCESSING
        payment.phone_number = msisdn
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "live",
            "provider": Payment.Provider.MTN_MOMO,
            "mtn_reference_id": reference_id,
        }
        payment.save()
        return {
            "reference": reference_id,
            "status": "processing",
            "integration_mode": "live",
            "provider": Payment.Provider.MTN_MOMO,
            "message": "MTN MoMo payment request sent — approve the prompt on your phone.",
            "requires_manual_confirm": False,
            "poll_status": True,
        }

    @staticmethod
    def initiate_airtel_payment(payment, phone: str) -> dict:
        client = AirtelMoneyClient()
        dial = COUNTRY_DIAL_CODES.get(payment.payer.country, "256")
        msisdn = normalize_msisdn(phone, dial)

        if not client.is_configured():
            return MobileMoneyService._simulated_result(payment, Payment.Provider.AIRTEL_MONEY, msisdn)

        transaction_id = str(payment.id)
        try:
            result = client.collect_payment(
                transaction_id=transaction_id,
                amount=float(payment.amount),
                phone=msisdn,
                reference=str(payment.order_id),
            )
        except AirtelMoneyError as exc:
            payment.status = Payment.Status.FAILED
            payment.metadata = {**(payment.metadata or {}), "error": str(exc)}
            payment.save()
            raise

        reference = result.get("data", {}).get("transaction", {}).get("id", transaction_id)
        payment.external_reference = reference
        payment.status = Payment.Status.PROCESSING
        payment.phone_number = msisdn
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "live",
            "provider": Payment.Provider.AIRTEL_MONEY,
            "airtel_transaction_id": transaction_id,
            "airtel_response": result,
        }
        payment.save()
        return {
            "reference": reference,
            "status": "processing",
            "integration_mode": "live",
            "provider": Payment.Provider.AIRTEL_MONEY,
            "message": "Airtel Money collection request sent — complete approval on your phone.",
            "requires_manual_confirm": False,
            "poll_status": True,
        }

    @staticmethod
    def initiate_mpesa_payment(payment, phone: str) -> dict:
        client = MPesaClient()
        msisdn = normalize_msisdn(phone, COUNTRY_DIAL_CODES.get(payment.payer.country, "254"))

        if not client.is_configured():
            return MobileMoneyService._simulated_result(payment, Payment.Provider.MPESA, msisdn)

        try:
            result = client.stk_push(
                amount=int(payment.amount),
                phone=msisdn,
                account_reference=str(payment.order_id),
                description=f"AgriPay order {payment.order_id}",
            )
        except MPesaError as exc:
            payment.status = Payment.Status.FAILED
            payment.metadata = {**(payment.metadata or {}), "error": str(exc)}
            payment.save()
            raise

        checkout_id = result.get("CheckoutRequestID", "")
        payment.external_reference = checkout_id
        payment.status = Payment.Status.PROCESSING
        payment.phone_number = msisdn
        payment.metadata = {
            **(payment.metadata or {}),
            "integration_mode": "live",
            "provider": Payment.Provider.MPESA,
            "mpesa_checkout_request_id": checkout_id,
            "mpesa_response": result,
        }
        payment.save()
        return {
            "reference": checkout_id,
            "status": "processing",
            "integration_mode": "live",
            "provider": Payment.Provider.MPESA,
            "message": result.get("CustomerMessage", "M-Pesa STK push sent — enter PIN on your phone."),
            "requires_manual_confirm": False,
            "poll_status": True,
        }

    @staticmethod
    def sync_provider_status(payment) -> dict:
        """Poll provider for latest status; returns normalized status payload."""
        mode = (payment.metadata or {}).get("integration_mode", "simulated")
        if mode == "simulated":
            return {
                "status": payment.status,
                "integration_mode": "simulated",
                "provider_status": "simulated",
            }

        if payment.provider == Payment.Provider.MTN_MOMO:
            client = MTNMoMoClient()
            ref = payment.metadata.get("mtn_reference_id") or payment.external_reference
            data = client.get_transaction_status(ref)
            provider_status = data.get("status", "PENDING")
            MobileMoneyService._apply_provider_status(payment, provider_status)
            return {
                "status": payment.status,
                "integration_mode": "live",
                "provider_status": provider_status,
                "raw": data,
            }

        if payment.provider == Payment.Provider.AIRTEL_MONEY:
            client = AirtelMoneyClient()
            tx_id = payment.metadata.get("airtel_transaction_id", str(payment.id))
            data = client.get_transaction_status(tx_id)
            provider_status = data.get("data", {}).get("transaction", {}).get("status", "PENDING")
            MobileMoneyService._apply_provider_status(payment, provider_status)
            return {
                "status": payment.status,
                "integration_mode": "live",
                "provider_status": provider_status,
                "raw": data,
            }

        return {
            "status": payment.status,
            "integration_mode": mode,
            "provider_status": payment.status,
            "message": "M-Pesa status is updated via callback webhook.",
        }

    @staticmethod
    def _apply_provider_status(payment, provider_status: str) -> None:
        success_states = {"SUCCESSFUL", "TS", "SUCCESS", "COMPLETED"}
        fail_states = {"FAILED", "TF", "FAILURE", "CANCELLED", "EXPIRED"}

        normalized = (provider_status or "").upper()
        if normalized in success_states:
            payment.status = Payment.Status.COMPLETED
        elif normalized in fail_states:
            payment.status = Payment.Status.FAILED
        else:
            payment.status = Payment.Status.PROCESSING
        payment.metadata = {
            **(payment.metadata or {}),
            "last_provider_status": provider_status,
        }
        payment.save(update_fields=["status", "metadata", "updated_at"])

    @staticmethod
    def confirm_simulated_payment(payment) -> dict:
        mode = (payment.metadata or {}).get("integration_mode", "simulated")
        if mode != "simulated":
            raise ValueError("Manual confirm is only available for simulated mobile money payments.")
        payment.status = Payment.Status.COMPLETED
        payment.save(update_fields=["status", "updated_at"])
        return {"status": "completed", "reference": payment.external_reference}
