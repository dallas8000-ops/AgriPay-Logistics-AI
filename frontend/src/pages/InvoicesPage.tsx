import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { useAuth } from '../context/AuthContext';
import { formatCurrency, invoiceApi, type Invoice } from '../lib/api';
import { publicPayUrl } from '../lib/locale';
import { phonePlaceholder } from '../lib/locale';

export default function InvoicesPage() {
  const { user } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    description: '',
    amount: '',
  });
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedRef, setCopiedRef] = useState<string | null>(null);

  const copyPayLink = async (inv: Invoice) => {
    const url = publicPayUrl(inv.payment_reference);
    await navigator.clipboard.writeText(url);
    setCopiedRef(inv.payment_reference);
    setTimeout(() => setCopiedRef(null), 2000);
  };

  const load = () => {
    invoiceApi.list().then(setInvoices).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg('');
    try {
      await invoiceApi.create({
        ...form,
        amount: form.amount,
        currency: user?.currency,
      });
      setShowForm(false);
      setForm({ customer_name: '', customer_phone: '', customer_email: '', description: '', amount: '' });
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Failed to create invoice');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Payment Requests"
        subtitle="Send any customer a reference (INV-…) to pay your personal MoMo number — no marketplace listing required."
      />

      <button type="button" className="btn btn-primary btn-block" style={{ marginBottom: '1rem' }} onClick={() => setShowForm(true)}>
        + New payment request
      </button>

      {showForm && (
        <form className="card form-card" onSubmit={handleCreate} style={{ marginBottom: '1rem' }}>
          <h3 className="form-card-title">New invoice</h3>
          <div className="form-group">
            <label>Customer name</label>
            <input value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Customer phone</label>
            <input value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} placeholder={phonePlaceholder(user?.country)} />
          </div>
          <div className="form-group">
            <label>What is this payment for?</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required rows={3} />
          </div>
          <div className="form-group">
            <label>Amount ({user?.currency})</label>
            <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required min="1" />
          </div>
          {msg && <p className="error-msg">{msg}</p>}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Saving…' : 'Create'}</button>
            <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {invoices.length === 0 ? (
        <div className="empty-state-card">
          <span className="empty-state-icon">🧾</span>
          <p>No payment requests yet. Create one and share the INV reference with your customer.</p>
        </div>
      ) : (
        invoices.map((inv) => (
          <article key={inv.id} className="produce-card" style={{ marginBottom: '0.75rem' }}>
            <div className="produce-card-body">
              <div className="produce-card-top">
                <strong>{inv.customer_name}</strong>
                <span className={`badge${inv.status === 'paid' ? '' : ' badge-tier'}`}>{inv.status}</span>
              </div>
              <p className="produce-card-meta">{inv.description}</p>
              <p style={{ fontWeight: 700, color: 'var(--primary)', marginTop: '0.35rem' }}>
                {formatCurrency(inv.amount, inv.currency)}
              </p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Ref: <strong>{inv.payment_reference}</strong>
              </p>
              {inv.status === 'pending' && (
                <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <a href={publicPayUrl(inv.payment_reference)} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">
                    Open pay link
                  </a>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => copyPayLink(inv)}>
                    {copiedRef === inv.payment_reference ? 'Copied!' : 'Copy link'}
                  </button>
                  <Link to="/reconcile" className="btn btn-secondary btn-sm">Reconcile SMS</Link>
                </div>
              )}
            </div>
          </article>
        ))
      )}
    </div>
  );
}
