import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatCurrency, marketplaceApi, type Order } from '../lib/api';

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    marketplaceApi.orders().then((r) => setOrders(r.results)).catch(() => {});
  }, []);

  return (
    <div className="page">
      <h1 className="page-title">My Orders</h1>
      {orders.length === 0 ? (
        <p className="empty-state">No orders yet. Browse the marketplace to buy produce.</p>
      ) : (
        orders.map((o) => (
          <div key={o.id} className="card" style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>#{o.id} · {o.listing_detail?.crop || 'Produce'}</strong>
              <span className="badge">{o.status}</span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
              {o.quantity_kg} kg · {formatCurrency(o.total_amount, o.currency)}
            </p>
            {o.status === 'pending' && (
              <Link to={`/payment/${o.id}`} className="btn btn-primary btn-block" style={{ marginTop: '0.75rem', textAlign: 'center' }}>
                Pay Now
              </Link>
            )}
          </div>
        ))
      )}
    </div>
  );
}
