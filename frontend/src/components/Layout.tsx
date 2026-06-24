import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home, ShoppingBag, Truck, CreditCard, AlertCircle, Bell, Settings, LayoutDashboard, Leaf, BookOpen, FileText,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { isAgriMode, useCapabilities } from '../context/CapabilitiesContext';
import { useTheme } from '../context/ThemeContext';
import { notificationsApi } from '../lib/api';
import HonestyBanner from './HonestyBanner';
import './Layout.css';

const roleNav: Record<string, Array<{ to: string; icon: typeof Home; label: string }>> = {
  farmer: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/invoices', icon: FileText, label: 'Invoices' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
    { to: '/marketplace', icon: ShoppingBag, label: 'Sell' },
    { to: '/ai-pricing', icon: Leaf, label: 'Price guide' },
    { to: '/deliveries', icon: Truck, label: 'Deliveries' },
  ],
  vendor: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/invoices', icon: FileText, label: 'Invoices' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
    { to: '/marketplace', icon: ShoppingBag, label: 'Listings' },
  ],
  buyer: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/marketplace', icon: ShoppingBag, label: 'Market' },
    { to: '/orders', icon: CreditCard, label: 'Orders' },
    { to: '/disputes', icon: AlertCircle, label: 'Disputes' },
    { to: '/notifications', icon: Bell, label: 'Alerts' },
  ],
  driver: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/deliveries', icon: Truck, label: 'Jobs' },
    { to: '/notifications', icon: Bell, label: 'Alerts' },
  ],
  admin: [
    { to: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
    { to: '/disputes', icon: AlertCircle, label: 'Disputes' },
    { to: '/notifications', icon: Bell, label: 'Alerts' },
  ],
};

const smeRoleNav: Record<string, Array<{ to: string; icon: typeof Home; label: string }>> = {
  farmer: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/invoices', icon: FileText, label: 'Invoices' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
  ],
  vendor: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/invoices', icon: FileText, label: 'Invoices' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
  ],
  buyer: [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/orders', icon: CreditCard, label: 'Payments' },
  ],
  driver: roleNav.driver,
  admin: [
    { to: '/admin', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/reconcile', icon: BookOpen, label: 'Reconcile' },
    { to: '/orders', icon: CreditCard, label: 'Payments' },
  ],
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const caps = useCapabilities();
  const { theme, toggleTheme } = useTheme();
  const [unread, setUnread] = useState(0);
  const agri = isAgriMode(caps);
  const nav = agri
    ? (roleNav[user?.role || 'buyer'] || roleNav.buyer)
    : (smeRoleNav[user?.role || 'buyer'] || smeRoleNav.buyer);

  useEffect(() => {
    notificationsApi.unreadCount().then((r) => setUnread(r.count)).catch(() => {});
    const interval = setInterval(() => {
      notificationsApi.unreadCount().then((r) => setUnread(r.count)).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [user]);

  return (
    <div className="app-shell">
      {!navigator.onLine && (
        <div className="offline-banner">Offline mode — changes will sync when connected</div>
      )}
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-icon">🌾</span>
          <div>
            <strong>AgriPay</strong>
            <small>Logistics AI</small>
          </div>
        </div>
        <div className="header-actions">
          <NavLink to="/notifications" className="icon-btn notif-btn" aria-label="Notifications">
            <Bell size={20} />
            {unread > 0 && <span className="notif-badge">{unread > 9 ? '9+' : unread}</span>}
          </NavLink>
          <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <NavLink to="/settings" className="icon-btn" aria-label="Settings">
            <Settings size={20} />
          </NavLink>
        </div>
      </header>

      <main className="app-main">{children}</main>

      <HonestyBanner />

      <nav className="bottom-nav">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`} end={to === '/' || to === '/admin'}>
            <Icon size={22} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
