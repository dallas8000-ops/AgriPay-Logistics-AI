import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { formatCurrency, invoiceApi, type PersonalPaymentInstructions } from '../lib/api';

export default function PublicPayPage() {
  const { ref } = useParams();
  const [instructions, setInstructions] = useState<PersonalPaymentInstructions | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ref) return;
    invoiceApi.publicInstructions(ref).then(setInstructions).catch((e) => {
      setError(e instanceof Error ? e.message : 'Payment request not found');
    });
  }, [ref]);

  if (error) {
    return (
      <div className="auth-page">
        <div className="card auth-form" style={{ maxWidth: 420 }}>
          <h2>Payment link</h2>
          <p className="error-msg">{error}</p>
          <Link to="/login" className="btn btn-secondary btn-block">Sign in to AgriPay</Link>
        </div>
      </div>
    );
  }

  if (!instructions) {
    return (
      <div className="auth-page">
        <p className="empty-state">Loading payment details…</p>
      </div>
    );
  }

  if (instructions.status === 'paid' || instructions.status === 'cancelled') {
    return (
      <div className="auth-page">
        <div className="card auth-form" style={{ maxWidth: 420 }}>
          <h2>{instructions.payment_reference}</h2>
          <p>{instructions.message || 'This payment request is no longer pending.'}</p>
          <Link to="/login" className="btn btn-primary btn-block">Open AgriPay</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page auth-page--split">
      <aside className="auth-showcase">
        <span className="auth-logo">🌾</span>
        <h1>AgriPay</h1>
        <p className="auth-tagline">Pay {instructions.seller_name} via mobile money — no app login required.</p>
      </aside>
      <div className="card auth-form">
        <h2>Pay {instructions.payment_reference}</h2>
        <p className="auth-form-sub">{instructions.description || 'Payment request'}</p>
        <p style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--primary)', margin: '0.75rem 0' }}>
          {formatCurrency(instructions.amount, instructions.currency)}
        </p>
        <div className="stat-card" style={{ marginBottom: '1rem', padding: '1rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Send to</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{instructions.payee_phone}</div>
          <div style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>
            Reference: <strong>{instructions.payment_reference}</strong>
          </div>
        </div>
        <ol style={{ fontSize: '0.85rem', color: 'var(--text-muted)', paddingLeft: '1.25rem', marginBottom: '1rem' }}>
          {instructions.instructions.map((step) => (
            <li key={step} style={{ marginBottom: '0.35rem' }}>{step}</li>
          ))}
        </ol>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          The seller confirms payment by pasting their M-Pesa/MoMo SMS on the Reconcile screen.
        </p>
        <Link to="/login" className="btn btn-secondary btn-block" style={{ marginTop: '1rem' }}>
          I have an AgriPay account
        </Link>
      </div>
    </div>
  );
}
