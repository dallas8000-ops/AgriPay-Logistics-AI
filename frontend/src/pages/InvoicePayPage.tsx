import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { flutterwaveLive, useCapabilities } from '../context/CapabilitiesContext';
import { formatCurrency, invoiceApi, type PersonalPaymentInstructions } from '../lib/api';

export default function InvoicePayPage() {
  const { id } = useParams();
  const caps = useCapabilities();
  const [instructions, setInstructions] = useState<PersonalPaymentInstructions | null>(null);
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const invoiceId = parseInt(id || '0');
    invoiceApi.instructions(invoiceId).then(setInstructions).catch(() => {});
  }, [id]);

  const payWithFlutterwave = async () => {
    const invoiceId = parseInt(id || '0');
    setLoading(true);
    setMsg('');
    try {
      const res = await invoiceApi.pay(invoiceId);
      if (res.checkout?.link) {
        window.location.href = res.checkout.link;
        return;
      }
      setMsg('No checkout link returned.');
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Checkout unavailable');
    } finally {
      setLoading(false);
    }
  };

  if (!instructions) {
    return <div className="page"><p className="empty-state">Loading payment details…</p></div>;
  }

  return (
    <div className="page">
      <h1 className="page-title">Pay {instructions.payment_reference}</h1>
      <div className="card">
        <p style={{ marginBottom: '0.5rem' }}>{instructions.description || 'Payment request'}</p>
        <p style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
          {formatCurrency(instructions.amount, instructions.currency)}
        </p>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          To: <strong>{instructions.seller_name}</strong>
        </p>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <span className="badge" style={{ marginBottom: '0.75rem', display: 'inline-block' }}>
          Personal transfer (no merchant account)
        </span>
        <div className="stat-card" style={{ marginBottom: '1rem', padding: '1rem' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{instructions.payee_phone}</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Reference: <strong>{instructions.payment_reference}</strong>
          </div>
        </div>
        <ol style={{ fontSize: '0.85rem', color: 'var(--text-muted)', paddingLeft: '1.25rem' }}>
          {instructions.instructions.map((step) => (
            <li key={step} style={{ marginBottom: '0.35rem' }}>{step}</li>
          ))}
        </ol>
      </div>

      {flutterwaveLive(caps) && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <p style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
            Or pay online via Flutterwave (MTN, Airtel, M-Pesa, card) when aggregator keys are configured.
          </p>
          <button type="button" className="btn btn-primary btn-block" onClick={payWithFlutterwave} disabled={loading}>
            {loading ? 'Opening checkout…' : 'Pay with Flutterwave'}
          </button>
        </div>
      )}

      {msg && <p className="error-msg" style={{ marginTop: '0.75rem' }}>{msg}</p>}
      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '1rem' }}>
        <Link to="/invoices">← Back to payment requests</Link>
      </p>
    </div>
  );
}
