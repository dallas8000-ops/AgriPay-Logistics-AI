import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { formatCurrency, marketplaceApi, paymentsApi, type Order } from '../lib/api';

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

export default function PaymentPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<Order | null>(null);
  const [provider, setProvider] = useState('mtn_momo');
  const [phone, setPhone] = useState('');
  const [checkout, setCheckout] = useState<Record<string, unknown> | null>(null);
  const [paymentId, setPaymentId] = useState('');
  const [stripePromise, setStripePromise] = useState<ReturnType<typeof loadStripe> | null>(null);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    marketplaceApi.orders().then((r) => {
      const o = r.results.find((x) => x.id === parseInt(orderId || '0'));
      setOrder(o || null);
    });
    paymentsApi.config().then((cfg) => {
      if (cfg.stripe_publishable_key) {
        setStripePromise(loadStripe(cfg.stripe_publishable_key));
      }
    });
  }, [orderId]);

  const initiatePayment = async () => {
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

  const confirmSandbox = async () => {
    if (!paymentId) return;
    await paymentsApi.confirm(paymentId);
    navigate('/deliveries');
  };

  if (!order) return <div className="page"><p className="empty-state">Loading order…</p></div>;

  return (
    <div className="page">
      <h1 className="page-title">Payment</h1>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <strong>{order.listing_detail?.crop || 'Produce'}</strong>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{order.quantity_kg} kg</p>
        <p style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)', marginTop: '0.5rem' }}>
          {formatCurrency(order.total_amount, order.currency)}
        </p>
      </div>

      {!checkout ? (
        <>
          <div className="card">
            <div className="form-group">
              <label>Payment Method</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="mtn_momo">MTN Mobile Money</option>
                <option value="airtel_money">Airtel Money</option>
                <option value="mpesa">M-Pesa</option>
                <option value="stripe">Stripe (International Card)</option>
              </select>
            </div>
            {provider !== 'stripe' && (
              <div className="form-group">
                <label>Mobile Money Number</label>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+256…" />
              </div>
            )}
            {msg && <p className="error-msg">{msg}</p>}
            <button className="btn btn-primary btn-block" onClick={initiatePayment}>
              Continue to Pay
            </button>
          </div>
        </>
      ) : provider === 'stripe' && checkout.client_secret && stripePromise ? (
        <div className="card">
          <Elements stripe={stripePromise} options={{ clientSecret: checkout.client_secret as string }}>
            <StripeCheckout
              paymentId={paymentId}
              onSuccess={() => navigate('/deliveries')}
            />
          </Elements>
          {Boolean(checkout.sandbox) && (
            <button className="btn btn-secondary btn-block" style={{ marginTop: '0.75rem' }} onClick={confirmSandbox}>
              Confirm Sandbox Payment
            </button>
          )}
        </div>
      ) : (
        <div className="card">
          <p style={{ marginBottom: '0.75rem' }}>
            {(checkout.message as string) || 'Payment initiated'}
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Reference: {checkout.reference as string}
          </p>
          <button className="btn btn-primary btn-block" style={{ marginTop: '1rem' }} onClick={confirmSandbox}>
            Confirm Payment (Sandbox)
          </button>
        </div>
      )}
    </div>
  );
}
