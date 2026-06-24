export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

export const COUNTRIES = {
  UG: { name: 'Uganda', currency: 'UGX', flag: '🇺🇬' },
  KE: { name: 'Kenya', currency: 'KES', flag: '🇰🇪' },
  TZ: { name: 'Tanzania', currency: 'TZS', flag: '🇹🇿' },
  RW: { name: 'Rwanda', currency: 'RWF', flag: '🇷🇼' },
} as const;

export type UserRole = 'farmer' | 'vendor' | 'buyer' | 'driver' | 'admin';
export type CountryCode = keyof typeof COUNTRIES;

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  country: CountryCode;
  phone: string;
  currency: string;
  is_verified: boolean;
}

export interface ProduceListing {
  id: number;
  seller: number;
  seller_name: string;
  crop: string;
  variety: string;
  quantity_kg: string;
  unit_price: string;
  currency: string;
  location: string;
  country: CountryCode;
  season: string;
  description: string;
  ai_suggested_price: string | null;
  status: string;
  created_at: string;
}

export interface Order {
  id: number;
  listing: number;
  listing_detail?: ProduceListing;
  buyer: number;
  buyer_name: string;
  quantity_kg: string;
  total_amount: string;
  currency: string;
  delivery_address: string;
  payment_reference?: string;
  collection_method?: string;
  status: string;
  created_at: string;
}

export interface Delivery {
  id: number;
  order: number;
  order_id: number;
  driver: number | null;
  driver_name: string | null;
  status: string;
  pickup_location: string;
  dropoff_location: string;
  route_summary: string;
  tracking_events: Array<{ status: string; note: string; timestamp: string }>;
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  channel: string;
  is_read: boolean;
  created_at: string;
}

export interface Dispute {
  id: number;
  order: number;
  category: string;
  description: string;
  status: string;
  raised_by_name: string;
  created_at: string;
}

export interface PriceEstimate {
  crop: string;
  unit_price: number;
  total_estimate: number;
  currency: string;
  confidence: number;
  risk_score: { level: string; score: number };
  summary: string;
  method?: string;
  method_note?: string;
}

export interface Capabilities {
  product_mode: 'agri' | 'sme_payments';
  product_name: string;
  tagline: string;
  invoices?: { status: string; description: string };
  collection: {
    personal_transfer: { status: string; description: string };
    sms_reconciliation: { status: string; description: string };
    merchant_api: {
      status: string;
      providers: Record<string, string>;
      description: string;
    };
    stripe: { status: string; description: string };
    flutterwave?: { status: string; description: string };
  };
  notifications: {
    in_app: { status: string };
    sms: { status: string; description: string };
    whatsapp: { status: string; description: string };
  };
  ai_pricing: { status: string; description: string; available: boolean };
  marketplace: { status: string; vertical: string; available: boolean; description: string };
  logistics: { status: string; available: boolean; description: string };
  warnings: string[];
}

export interface PaymentConfig {
  stripe_publishable_key: string;
  stripe_integration_mode?: 'live' | 'simulated';
  default_collection_mode?: 'personal_transfer' | 'integrated';
  personal_transfer_description?: string;
  providers: Array<{
    id: string;
    name: string;
    countries: string[];
    integration_mode: 'live' | 'simulated';
  }>;
}

export interface PersonalPaymentInstructions {
  collection_mode: string;
  requires_merchant_account: boolean;
  seller_name: string;
  payee_phone: string;
  provider: string;
  provider_label: string;
  amount: string;
  currency: string;
  payment_reference: string;
  status?: string;
  message?: string;
  description?: string;
  customer_name?: string;
  invoice_id?: number;
  instructions: string[];
}

export interface Invoice {
  id: number;
  seller: number;
  seller_name: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  description: string;
  amount: string;
  currency: string;
  payment_reference: string;
  status: string;
  collection_method: string;
  due_date: string | null;
  notes: string;
  created_at: string;
}

export interface LedgerEntry {
  id: number;
  owner: number;
  recorded_by: number;
  order: number | null;
  invoice: number | null;
  order_reference: string;
  invoice_reference: string;
  source: string;
  status: string;
  raw_sms: string;
  amount: string | null;
  currency: string;
  provider: string;
  txn_reference: string;
  payer_phone: string;
  parse_confidence: string;
  notes: string;
  suggested_order_ids: number[];
  suggested_invoice_ids: number[];
  created_at: string;
}

export interface ReconciliationSummary {
  pending_orders_count: number;
  pending_invoices_count?: number;
  expected_collections: string;
  recorded_collections: string;
  unmatched_entries_count: number;
  matched_entries_count: number;
  collection_mode: string;
  message: string;
}

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export async function publicApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const capabilitiesApi = {
  get: () => api<Capabilities>('/system/capabilities/'),
};

export const authApi = {
  login: (username: string, password: string) =>
    api<{ access: string; refresh: string }>('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  register: (data: Record<string, string>) =>
    api<User>('/auth/register/', { method: 'POST', body: JSON.stringify(data) }),
  me: () => api<User>('/auth/me/'),
  onboarding: () => api<{ onboarding_complete: boolean; profile: unknown }>('/auth/onboarding/'),
  submitOnboarding: (data: Record<string, unknown>) =>
    api('/auth/onboarding/', { method: 'POST', body: JSON.stringify(data) }),
  adminStats: () => api<Record<string, unknown>>('/auth/admin/stats/'),
};

export const marketplaceApi = {
  listings: (params?: string) =>
    api<{ results: ProduceListing[] }>(`/marketplace/listings/${params ? `?${params}` : ''}`),
  createListing: (data: Record<string, unknown>) =>
    api<ProduceListing>('/marketplace/listings/', { method: 'POST', body: JSON.stringify(data) }),
  orders: () => api<{ results: Order[] }>('/marketplace/orders/'),
  createOrder: (data: { listing: number; quantity_kg: number; delivery_address: string }) =>
    api<Order>('/marketplace/orders/', { method: 'POST', body: JSON.stringify(data) }),
};

export const logisticsApi = {
  deliveries: () => api<{ results: Delivery[] }>('/logistics/'),
  assignDriver: (id: number, driver_id: number) =>
    api(`/logistics/${id}/assign_driver/`, {
      method: 'POST',
      body: JSON.stringify({ driver_id }),
    }),
  updateLocation: (id: number, data: Record<string, unknown>) =>
    api(`/logistics/${id}/update_location/`, { method: 'POST', body: JSON.stringify(data) }),
  availableDrivers: () => api<Array<{ id: number; username: string; vehicle: string }>>('/logistics/available_drivers/'),
  submitProof: (id: number, data: Record<string, string>) =>
    api(`/logistics/${id}/submit_proof/`, { method: 'POST', body: JSON.stringify(data) }),
};

export const paymentsApi = {
  config: () => api<PaymentConfig>('/payments/config/'),
  instructions: (order_id: number) =>
    api<PersonalPaymentInstructions>(`/payments/collect/instructions/?order_id=${order_id}`),
  buyerClaim: (data: { order_id: number; raw_sms?: string; notes?: string }) =>
    api<{ entry: LedgerEntry; message: string }>('/payments/collect/buyer-claim/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  create: (order_id: number, provider: string, phone_number?: string) =>
    api<{ payment: unknown; checkout: Record<string, unknown> }>('/payments/', {
      method: 'POST',
      body: JSON.stringify({ order_id, provider, phone_number }),
    }),
  confirm: (id: string) =>
    api(`/payments/${id}/confirm/`, { method: 'POST' }),
  status: (id: string) =>
    api<{ status: string; integration_mode?: string; provider_status?: string; message?: string }>(
      `/payments/${id}/status/`
    ),
};

export const invoiceApi = {
  list: () => api<{ results: Invoice[] }>('/payments/invoices/').then((r) => r.results),
  create: (data: Partial<Invoice>) =>
    api<Invoice>('/payments/invoices/', { method: 'POST', body: JSON.stringify(data) }),
  instructions: (id: number) =>
    api<PersonalPaymentInstructions & { invoice_id?: number; customer_name?: string; description?: string }>(
      `/payments/invoices/${id}/instructions/`
    ),
  pay: (id: number, redirect_url?: string) =>
    api<{ payment_id: string; checkout: { link: string; message: string } }>(`/payments/invoices/${id}/pay/`, {
      method: 'POST',
      body: JSON.stringify({ redirect_url: redirect_url || window.location.origin + `/invoices/${id}/paid` }),
    }),
  summary: () => api<{ pending_count: number; pending_amount: string; currency: string }>('/payments/invoices/summary/'),
  publicInstructions: (paymentReference: string) =>
    publicApi<PersonalPaymentInstructions & { status?: string; message?: string }>(
      `/payments/invoices/public/${encodeURIComponent(paymentReference)}/`,
    ),
};

export const ledgerApi = {
  list: () => api<{ results: LedgerEntry[] }>('/payments/ledger/').then((r) => r.results),
  create: (data: { raw_sms?: string; source?: string; notes?: string }) =>
    api<LedgerEntry>('/payments/ledger/', { method: 'POST', body: JSON.stringify(data) }),
  parseSms: (text: string) =>
    api<Record<string, unknown>>('/payments/ledger/parse_sms/', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  summary: () => api<ReconciliationSummary>('/payments/ledger/summary/'),
  match: (id: number, order_id: number) =>
    api(`/payments/ledger/${id}/match/`, {
      method: 'POST',
      body: JSON.stringify({ order_id }),
    }),
  matchInvoice: (id: number, invoice_id: number) =>
    api(`/payments/ledger/${id}/match-invoice/`, {
      method: 'POST',
      body: JSON.stringify({ invoice_id }),
    }),
  exportCsv: async () => {
    const token = getToken();
    const res = await fetch(`${API_URL}/payments/ledger/export-csv/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'agripay-ledger.csv';
    a.click();
    URL.revokeObjectURL(url);
  },
};

export const aiApi = {
  priceEstimate: (data: { crop: string; quantity_kg: number; country?: string; season?: string }) =>
    api<PriceEstimate>('/ai/price-estimate/', { method: 'POST', body: JSON.stringify(data) }),
  routeSummary: (data: { pickup: string; dropoff: string }) =>
    api<{ summary: string }>('/ai/route-summary/', { method: 'POST', body: JSON.stringify(data) }),
  buyerScore: () => api<{ score: number; tier: string; summary: string }>('/ai/buyer-score/'),
};

export const disputesApi = {
  list: () => api<{ results: Dispute[] }>('/disputes/'),
  create: (data: { order: number; category: string; description: string }) =>
    api<Dispute>('/disputes/', { method: 'POST', body: JSON.stringify(data) }),
};

export const notificationsApi = {
  list: () => api<{ results: Notification[] }>('/notifications/'),
  unreadCount: () => api<{ count: number }>('/notifications/unread_count/'),
  markRead: (id: number) => api(`/notifications/${id}/mark_read/`, { method: 'POST' }),
  markAllRead: () => api('/notifications/mark_all_read/', { method: 'POST' }),
};

export function formatCurrency(amount: string | number, currency: string) {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 0 }).format(num);
}

export function queueOfflineAction(action: { url: string; method: string; body?: unknown }) {
  const queue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
  queue.push({ ...action, timestamp: Date.now() });
  localStorage.setItem('offline_queue', JSON.stringify(queue));
}

export async function syncOfflineQueue() {
  if (!navigator.onLine) return;
  const queue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
  if (!queue.length) return;
  const remaining = [];
  for (const action of queue) {
    try {
      await api(action.url.replace(API_URL, ''), {
        method: action.method,
        body: action.body ? JSON.stringify(action.body) : undefined,
      });
    } catch {
      remaining.push(action);
    }
  }
  localStorage.setItem('offline_queue', JSON.stringify(remaining));
}
