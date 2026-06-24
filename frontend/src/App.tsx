import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CapabilitiesProvider, isAgriMode, useCapabilities } from './context/CapabilitiesContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HomePage from './pages/HomePage';
import OnboardingPage from './pages/OnboardingPage';
import MarketplacePage from './pages/MarketplacePage';
import OrdersPage from './pages/OrdersPage';
import DeliveriesPage from './pages/DeliveriesPage';
import AIPricingPage from './pages/AIPricingPage';
import DisputesPage from './pages/DisputesPage';
import NotificationsPage from './pages/NotificationsPage';
import SettingsPage from './pages/SettingsPage';
import AdminPage from './pages/AdminPage';
import PaymentPage from './pages/PaymentPage';
import InvoicesPage from './pages/InvoicesPage';
import InvoicePayPage from './pages/InvoicePayPage';
import ReconciliationPage from './pages/ReconciliationPage';
import './auth.css';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page"><p className="empty-state">Loading…</p></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function AgriOnlyRoute({ children }: { children: React.ReactNode }) {
  const caps = useCapabilities();
  if (!isAgriMode(caps)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
      <Route path="/onboarding" element={<PrivateRoute><OnboardingPage /></PrivateRoute>} />
      <Route path="/marketplace" element={<PrivateRoute><AgriOnlyRoute><MarketplacePage /></AgriOnlyRoute></PrivateRoute>} />
      <Route path="/orders" element={<PrivateRoute><OrdersPage /></PrivateRoute>} />
      <Route path="/deliveries" element={<PrivateRoute><AgriOnlyRoute><DeliveriesPage /></AgriOnlyRoute></PrivateRoute>} />
      <Route path="/ai-pricing" element={<PrivateRoute><AgriOnlyRoute><AIPricingPage /></AgriOnlyRoute></PrivateRoute>} />
      <Route path="/disputes" element={<PrivateRoute><DisputesPage /></PrivateRoute>} />
      <Route path="/notifications" element={<PrivateRoute><NotificationsPage /></PrivateRoute>} />
      <Route path="/admin" element={<PrivateRoute><AdminPage /></PrivateRoute>} />
      <Route path="/settings" element={<PrivateRoute><SettingsPage /></PrivateRoute>} />
      <Route path="/payment/:orderId" element={<PrivateRoute><PaymentPage /></PrivateRoute>} />
      <Route path="/reconcile" element={<PrivateRoute><ReconciliationPage /></PrivateRoute>} />
      <Route path="/invoices" element={<PrivateRoute><InvoicesPage /></PrivateRoute>} />
      <Route path="/invoices/:id/pay" element={<PrivateRoute><InvoicePayPage /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <CapabilitiesProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </CapabilitiesProvider>
    </ThemeProvider>
  );
}
