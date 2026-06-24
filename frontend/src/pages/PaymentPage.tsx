import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { merchantApiLive, stripeLive, useCapabilities } from '../context/CapabilitiesContext';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import {
  formatCurrency,
  marketplaceApi,
  paymentsApi,
  type Order,
  type PaymentConfig,
  type PersonalPaymentInstructions,
} from '../lib/api';

function StripeCheckout({ paymentId, onSuccess }: { paymentId: string; onSuccess: () => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    setError('');
    const { error: submitError } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: window.location.origin + '/orders' },
      redirect: 'if_required',
    });
    if (submitError) {
      setError(submitError.message || 'Payment failed');
      setLoading(false);
      return;
    }
    await paymentsApi.confirm(paymentId);
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      {error && <p className="error-msg">{error}</p>}
      <button type="submit" className="btn btn-primary btn-block" style={{ marginTop: '1rem' }} disabled={!stripe || loading}>
        {loading ? 'Processing…' : 'Pay with Card'}
      </button>
    </form>
  );
}

function IntegrationBadge({ mode }: { mode?: string }) {
  const isLive = mode === 'live';
  return (
    <span className={`badge${isLive ? '' : ' badge-tier'}`} style={{ marginBottom: '0.75rem', display: 'inline-block' }}>
      {isLive ? 'Live merchant API' : 'Simulated — dev only'}
    </span>
  );
}

export default function PaymentPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<Order | null>(null);
  const [config, setConfig] = useState<PaymentConfig | null>(null);
  const [instructions, setInstructions] = useState<PersonalPaymentInstructions | null>(null);
  const [mode, setMode] = useState<'personal' | 'merchant'>('personal');
  const [provider, setProvider] = useState('mtn_momo');
  const [phone, setPhone] = useState('');
  const [buyerSms, setBuyerSms] = useState('');
  const [checkout, setCheckout] = useState<Record<string, unknown> | null>(null);
  const [paymentId, setPaymentId] = useState('');
  const [stripePromise, setStripePromise] = useState<ReturnType<typeof loadStripe> | null>(null);
  const [msg, setMsg] = useState('');
  const [polling, setPolling] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const caps = useCapabilities();
  const showMerchant = merchantApiLive(caps) || stripeLive(caps);

  useEffect(() => {
    const oid = parseInt(orderId || '0');
    marketplaceApi.orders().then((r) => {
      const o = r.results.find((x) => x.id === oid);
      setOrder(o || null);
    });
    paymentsApi.config().then((cfg) => {
      setConfig(cfg);
      if (cfg.stripe_publishable_key) {
        setStripePromise(loadStripe(cfg.stripe_publishable_key));
      }
    });
    paymentsApi.instructions(oid).then(setInstructions).catch(() => {});
  }, [orderId]);

  const providerMode = config?.providers.find((p) => p.id === provider)?.integration_mode;

  const initiateMerchantPayment = async () => {
    if (!order) return;
    try {
      const res = await paymentsApi.create(order.id, provider, phone);
      setCheckout(res.checkout);
      setPaymentId((res.payment as { id: string }).id);
      setMsg('');
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Payment failed');
    }
  };

  const confirmSimulated = async () => {
    if (!paymentId) return;
    await paymentsApi.confirm(paymentId);
    navigate('/deliveries');
  };

  const pollStatus = async () => {
    if (!paymentId) return;
    setPolling(true);
    setMsg('');
    try {
      const result = await paymentsApi.status(paymentId);
      if (result.status === 'completed') {
        navigate('/deliveries');
        return;
      }
      if (result.status === 'failed') {
        setMsg('Payment failed or was declined. Try again or use another method.');
        return;
      }
      setMsg('Still waiting for approval on your phone…');
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Could not check payment status');
    } finally {
      setPolling(false);
    }
  };

  const reportPayment = async () => {
    if (!order) return;
    setClaiming(true);
    setMsg('');
    try {
      const res = await paymentsApi.buyerClaim({
        order_id: order.id,
        raw_sms: buyerSms,
        notes: 'Buyer reported payment sent via personal transfer',
      });
      setMsg(res.message);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Could not report payment');
    } finally {
      setClaiming(false);
    }
  };

  useEffect(() => {
    if (!paymentId || !checkout?.poll_status) return;
    const interval = setInterval(() => {
      paymentsApi.status(paymentId).then((result) => {
        if (result.status === 'completed') navigate('/deliveries');
        if (result.status === 'failed') setMsg('Payment failed or was declined.');
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [paymentId, checkout, navigate]);

  if (!order) return <div className="page"><p className="empty-state">Loading order…</p></div>;

  const reference = instructions?.payment_reference || order.payment_reference || `AGR-${order.id}`;

  return (
    <div className="page">
      <h1 className="page-title">Pay for Order</h1>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <strong>{order.listing_detail?.crop || 'Produce'}</strong>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{order.quantity_kg} kg</p>
        <p style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)', marginTop: '0.5rem' }}>
          {formatCurrency(order.total_amount, order.currency)}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          type="button"
          className={`btn${mode === 'personal' ? ' btn-primary' : ' btn-secondary'}`}
          onClick={() => { setMode('personal'); setCheckout(null); }}
        >
          Personal transfer
        </button>
        {showMerchant && (
          <button
            type="button"
            className={`btn${mode === 'merchant' ? ' btn-primary' : ' btn-secondary'}`}
            onClick={() => setMode('merchant')}
          >
            Merchant API
          </button>
        )}
      </div>

      {mode === 'personal' && instructions && !checkout && (
        <div className="card">
          <span className="badge" style={{ marginBottom: '0.75rem', display: 'inline-block' }}>
            No merchant account needed
          </span>
          <p style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>
            Send money to <strong>{instructions.seller_name}</strong>&apos;s personal {instructions.provider_label} number.
          </p>
          <div className="stat-card" style={{ marginBottom: '1rem', padding: '1rem' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{instructions.payee_phone}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Reference: <strong>{reference}</strong> (required)
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.5rem', color: 'var(--primary)' }}>
              {formatCurrency(instructions.amount, instructions.currency)}
            </div>
          </div>
          <ol style={{ fontSize: '0.85rem', color: 'var(--text-muted)', paddingLeft: '1.25rem', marginBottom: '1rem' }}>
            {instructions.instructions.map((step) => (
              <li key={step} style={{ marginBottom: '0.35rem' }}>{step}</li>
            ))}
          </ol>
          <div className="form-group">
            <label>Paste confirmation SMS (optional)</label>
            <textarea
              value={buyerSms}
              onChange={(e) => setBuyerSms(e.target.value)}
              rows={3}
              placeholder="Paste the SMS you received after sending payment"
            />
          </div>
          <button type="button" className="btn btn-primary btn-block" onClick={reportPayment} disabled={claiming}>
            {claiming ? 'Reporting…' : 'I have paid'}
          </button>
          {msg && <p className="toast-msg" style={{ marginTop: '0.75rem' }}>{msg}</p>}
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
            The seller reconciles your payment from their SMS inbox — not a merchant API prompt.
          </p>
        </div>
      )}

      {mode === 'merchant' && !checkout && (
        <div className="card">
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            For sellers with a registered business / merchant account and provider API credentials.
          </p>
          <div className="form-group">
            <label>Payment Method</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              {config?.providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.integration_mode === 'live' ? 'live API' : 'simulated'})
                </option>
              )) ?? (
                <>
                  <option value="mtn_momo">MTN Mobile Money</option>
                  <option value="airtel_money">Airtel Money</option>
                  <option value="mpesa">M-Pesa</option>
                  <option value="stripe">Stripe (International Card)</option>
                </>
              )}
            </select>
          </div>
          {providerMode && <IntegrationBadge mode={providerMode} />}
          {provider !== 'stripe' && (
            <div className="form-group">
              <label>Your Mobile Money Number</label>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+256…" />
            </div>
          )}
          {msg && <p className="error-msg">{msg}</p>}
          <button type="button" className="btn btn-primary btn-block" onClick={initiateMerchantPayment}>
            Continue with Merchant API
          </button>
        </div>
      )}

      {checkout && provider === 'stripe' && checkout.client_secret && stripePromise ? (
        <div className="card">
          <IntegrationBadge mode={checkout.integration_mode as string} />
          <Elements stripe={stripePromise} options={{ clientSecret: checkout.client_secret as string }}>
            <StripeCheckout
              paymentId={paymentId}
              onSuccess={() => navigate('/deliveries')}
            />
          </Elements>
          {Boolean(checkout.requires_manual_confirm) && (
            <button type="button" className="btn btn-secondary btn-block" style={{ marginTop: '0.75rem' }} onClick={confirmSimulated}>
              Confirm Simulated Stripe Payment
            </button>
          )}
        </div>
      ) : checkout ? (
        <div className="card">
          <IntegrationBadge mode={checkout.integration_mode as string} />
          <p style={{ marginBottom: '0.75rem' }}>
            {(checkout.message as string) || 'Payment initiated'}
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Reference: {checkout.reference as string}
          </p>
          {checkout.integration_mode === 'live' ? (
            <>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                Approve the prompt on your phone. This page will update automatically when the provider confirms payment.
              </p>
              <button type="button" className="btn btn-secondary btn-block" style={{ marginTop: '1rem' }} onClick={pollStatus} disabled={polling}>
                {polling ? 'Checking…' : 'Check Payment Status'}
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-primary btn-block" style={{ marginTop: '1rem' }} onClick={confirmSimulated}>
              Complete Simulated Payment (dev only)
            </button>
          )}
          {msg && <p className="error-msg" style={{ marginTop: '0.75rem' }}>{msg}</p>}
        </div>
      ) : null}
    </div>
  );
}
