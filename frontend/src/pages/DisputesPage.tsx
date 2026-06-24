import { useEffect, useState } from 'react';
import { disputesApi, marketplaceApi, type Dispute, type Order } from '../lib/api';

export default function DisputesPage() {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ order: '', category: 'quality', description: '' });

  useEffect(() => {
    disputesApi.list().then((r) => setDisputes(r.results)).catch(() => {});
    marketplaceApi.orders().then((r) => setOrders(r.results)).catch(() => {});
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await disputesApi.create({
      order: parseInt(form.order),
      category: form.category,
      description: form.description,
    });
    setShowForm(false);
    disputesApi.list().then((r) => setDisputes(r.results));
  };

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">Dispute Center</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>+ Raise</button>
      </div>

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: '1rem' }}>
          <div className="form-group">
            <label>Order</label>
            <select value={form.order} onChange={(e) => setForm({ ...form, order: e.target.value })} required>
              <option value="">Select order…</option>
              {orders.map((o) => (
                <option key={o.id} value={o.id}>#{o.id} — {o.listing_detail?.crop} ({o.status})</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Category</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="quality">Product Quality</option>
              <option value="quantity">Quantity Mismatch</option>
              <option value="payment">Payment Issue</option>
              <option value="delivery">Delivery Problem</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
          </div>
          <button type="submit" className="btn btn-primary btn-block">Submit Dispute</button>
        </form>
      )}

      {disputes.length === 0 ? (
        <p className="empty-state">No disputes. We're here if something goes wrong.</p>
      ) : (
        disputes.map((d) => (
          <div key={d.id} className="card" style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>#{d.id} · Order {d.order}</strong>
              <span className="badge">{d.status}</span>
            </div>
            <p style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>{d.category} — {d.description}</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Raised by {d.raised_by_name}
            </p>
          </div>
        ))
      )}
    </div>
  );
}
