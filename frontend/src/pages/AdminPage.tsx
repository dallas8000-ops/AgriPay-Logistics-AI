import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi, disputesApi, formatCurrency, logisticsApi, marketplaceApi, type Dispute, type Order } from '../lib/api';

interface AdminStats {
  users_by_role: Record<string, number>;
  total_listings: number;
  active_orders: number;
  deliveries_in_transit: number;
  open_disputes: number;
  payments_volume: number;
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [deliveries, setDeliveries] = useState<Array<{ id: number; status: string; order_id: number }>>([]);

  useEffect(() => {
    authApi.adminStats().then((s) => setStats(s as unknown as AdminStats)).catch(() => {});
    marketplaceApi.orders().then((r) => setOrders(r.results.slice(0, 5))).catch(() => {});
    disputesApi.list().then((r) => setDisputes(r.results.filter((d) => d.status === 'open').slice(0, 5))).catch(() => {});
    logisticsApi.deliveries().then((r) => setDeliveries(r.results.slice(0, 5))).catch(() => {});
  }, []);

  if (!stats) {
    return <div className="page"><p className="empty-state">Loading admin dashboard…</p></div>;
  }

  const totalUsers = Object.values(stats.users_by_role).reduce((a, b) => a + b, 0);

  return (
    <div className="page">
      <h1 className="page-title">Platform Admin</h1>

      <div className="grid-2">
        <div className="card stat-card">
          <div className="stat-value">{totalUsers}</div>
          <div className="stat-label">Total Users</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.total_listings}</div>
          <div className="stat-label">Listings</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.active_orders}</div>
          <div className="stat-label">Active Orders</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.deliveries_in_transit}</div>
          <div className="stat-label">In Transit</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.open_disputes}</div>
          <div className="stat-label">Open Disputes</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{formatCurrency(stats.payments_volume, 'KES')}</div>
          <div className="stat-label">Payment Volume</div>
        </div>
      </div>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginBottom: '0.75rem' }}>Users by Role</h3>
        {Object.entries(stats.users_by_role).map(([role, count]) => (
          <div key={role} className="list-item">
            <span style={{ textTransform: 'capitalize' }}>{role}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <h3>Recent Orders</h3>
          <Link to="/marketplace">View →</Link>
        </div>
        {orders.length === 0 ? (
          <p className="empty-state" style={{ padding: '1rem 0' }}>No orders</p>
        ) : (
          orders.map((o) => (
            <div key={o.id} className="list-item">
              <span>#{o.id} {o.listing_detail?.crop}</span>
              <span className="badge">{o.status}</span>
            </div>
          ))
        )}
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <h3>Open Disputes</h3>
          <Link to="/disputes">Resolve →</Link>
        </div>
        {disputes.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No open disputes</p>
        ) : (
          disputes.map((d) => (
            <div key={d.id} className="list-item">
              <span>#{d.id} · {d.category}</span>
              <span className="badge">{d.status}</span>
            </div>
          ))
        )}
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginBottom: '0.5rem' }}>Deliveries</h3>
        {deliveries.map((d) => (
          <div key={d.id} className="list-item">
            <span>Order #{d.order_id}</span>
            <span className="badge">{d.status}</span>
          </div>
        ))}
      </section>

      <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        Django admin: <a href="http://localhost:8000/admin/" target="_blank" rel="noreferrer">localhost:8000/admin</a>
      </p>
    </div>
  );
}
