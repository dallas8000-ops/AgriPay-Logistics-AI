import { Link, Navigate } from 'react-router-dom';
import {
  AlertCircle, Bell, CreditCard, Leaf, ShoppingBag, Sparkles, Truck, Wallet,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  aiApi, COUNTRIES, logisticsApi, marketplaceApi, notificationsApi,
  type ProduceListing,
} from '../lib/api';
import { ROLE_LABELS } from '../lib/crops';
import { ProduceCardLink } from '../components/ProduceCard';

const QUICK_ACTIONS: Record<string, Array<{ to: string; icon: typeof ShoppingBag; label: string; desc: string }>> = {
  farmer: [
    { to: '/marketplace', icon: ShoppingBag, label: 'Sell Produce', desc: 'List crops & set prices' },
    { to: '/ai-pricing', icon: Leaf, label: 'AI Pricing', desc: 'Smart market estimates' },
    { to: '/deliveries', icon: Truck, label: 'Deliveries', desc: 'Track shipments' },
    { to: '/notifications', icon: Bell, label: 'Alerts', desc: 'Orders & payments' },
  ],
  vendor: [
    { to: '/marketplace', icon: ShoppingBag, label: 'My Listings', desc: 'Manage inventory' },
    { to: '/ai-pricing', icon: Leaf, label: 'AI Pricing', desc: 'Optimize margins' },
    { to: '/notifications', icon: Bell, label: 'Alerts', desc: 'Buyer activity' },
  ],
  buyer: [
    { to: '/marketplace', icon: ShoppingBag, label: 'Browse Market', desc: 'Fresh produce near you' },
    { to: '/orders', icon: CreditCard, label: 'My Orders', desc: 'Pay & track purchases' },
    { to: '/disputes', icon: AlertCircle, label: 'Disputes', desc: 'Resolve issues' },
    { to: '/ai-pricing', icon: Sparkles, label: 'AI Insights', desc: 'Price intelligence' },
  ],
  driver: [
    { to: '/deliveries', icon: Truck, label: 'Delivery Jobs', desc: 'Accept & complete runs' },
    { to: '/notifications', icon: Bell, label: 'Alerts', desc: 'New assignments' },
  ],
};

export default function HomePage() {
  const { user } = useAuth();
  const [listings, setListings] = useState<ProduceListing[]>([]);
  const [buyerScore, setBuyerScore] = useState<{ score: number; tier: string; summary: string } | null>(null);
  const [stats, setStats] = useState({ orders: 0, deliveries: 0, unread: 0 });

  useEffect(() => {
    marketplaceApi.listings().then((r) => setListings(r.results.slice(0, 4))).catch(() => {});
    marketplaceApi.orders().then((r) => setStats((s) => ({ ...s, orders: r.results.length }))).catch(() => {});
    logisticsApi.deliveries().then((r) => setStats((s) => ({ ...s, deliveries: r.results.length }))).catch(() => {});
    notificationsApi.unreadCount().then((r) => setStats((s) => ({ ...s, unread: r.count }))).catch(() => {});
    if (user?.role === 'buyer') {
      aiApi.buyerScore().then(setBuyerScore).catch(() => {});
    }
  }, [user]);

  if (user?.role === 'admin') {
    return <Navigate to="/admin" replace />;
  }

  const country = user?.country ? COUNTRIES[user.country as keyof typeof COUNTRIES] : null;
  const actions = QUICK_ACTIONS[user?.role || 'buyer'] || QUICK_ACTIONS.buyer;
  const roleLabel = ROLE_LABELS[user?.role || 'buyer'] || 'Member';

  return (
    <div className="page dashboard-page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-content">
          <span className="dashboard-role-pill">{roleLabel}</span>
          <p className="welcome-greeting">Karibu, {user?.first_name || user?.username} 👋</p>
          <h1 className="dashboard-headline">Your AgriPay Hub</h1>
          {country && (
            <p className="welcome-meta">
              {country.flag} {country.name} · {user?.currency} · Mobile money ready
            </p>
          )}
        </div>
        <div className="dashboard-hero-pattern" aria-hidden />
      </section>

      <div className="stat-grid">
        <div className="stat-card stat-card--highlight">
          <Wallet size={18} className="stat-icon" />
          <div className="stat-value">{stats.orders}</div>
          <div className="stat-label">Orders</div>
        </div>
        <div className="stat-card">
          <Truck size={18} className="stat-icon" />
          <div className="stat-value">{stats.deliveries}</div>
          <div className="stat-label">Deliveries</div>
        </div>
        <div className="stat-card">
          <Bell size={18} className="stat-icon" />
          <div className="stat-value">{stats.unread}</div>
          <div className="stat-label">Alerts</div>
        </div>
      </div>

      {buyerScore && (
        <section className="card insight-card">
          <div className="insight-card-header">
            <Sparkles size={18} />
            <strong>Buyer Reliability Score</strong>
            <span className="badge badge-tier">{buyerScore.tier}</span>
          </div>
          <div className="insight-score-row">
            <div className="insight-score-bar">
              <div className="insight-score-fill" style={{ width: `${buyerScore.score}%` }} />
            </div>
            <span className="insight-score-value">{buyerScore.score}/100</span>
          </div>
          <p className="insight-summary">{buyerScore.summary}</p>
        </section>
      )}

      {!user?.is_verified && (
        <Link to="/onboarding" className="card onboarding-cta">
          <div>
            <strong>Complete your profile</strong>
            <p>Verify your {roleLabel.toLowerCase()} details to unlock payments & logistics</p>
          </div>
          <span className="onboarding-cta-arrow">→</span>
        </Link>
      )}

      <section className="dashboard-section">
        <h2 className="section-title">Quick Actions</h2>
        <div className="quick-action-grid">
          {actions.map(({ to, icon: Icon, label, desc }) => (
            <Link key={to} to={to} className="quick-action-card">
              <span className="quick-action-icon"><Icon size={20} /></span>
              <strong>{label}</strong>
              <span>{desc}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header-row">
          <h2 className="section-title">Payment Rails</h2>
        </div>
        <div className="payment-rails">
          <span className="payment-rail">📱 MTN MoMo</span>
          <span className="payment-rail">📱 Airtel Money</span>
          <span className="payment-rail">📱 M-Pesa</span>
          <span className="payment-rail">💳 Stripe</span>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header-row">
          <h2 className="section-title">Fresh Produce</h2>
          <Link to="/marketplace" className="section-link">View marketplace →</Link>
        </div>
        {listings.length === 0 ? (
          <div className="empty-state-card">
            <span className="empty-state-icon">🌾</span>
            <p>No listings yet — be the first to list produce in {country?.name || 'your region'}.</p>
            {(user?.role === 'farmer' || user?.role === 'vendor') && (
              <Link to="/marketplace" className="btn btn-primary">List Produce</Link>
            )}
          </div>
        ) : (
          <div className="produce-list">
            {listings.map((l) => (
              <ProduceCardLink key={l.id} listing={l} />
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Platform Coverage</h2>
        <div className="region-chips">
          {Object.entries(COUNTRIES).map(([code, c]) => (
            <span key={code} className={`region-chip${user?.country === code ? ' region-chip--active' : ''}`}>
              {c.flag} {c.name}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
