import { useEffect, useState } from 'react';
import { notificationsApi, type Notification } from '../lib/api';

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);

  const load = () => notificationsApi.list().then((r) => setItems(r.results)).catch(() => {});
  useEffect(() => { load(); }, []);

  const channelIcon = (ch: string) => {
    if (ch === 'sms') return '📱';
    if (ch === 'whatsapp') return '💬';
    return '🔔';
  };

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">Notifications</h1>
        <button className="btn btn-secondary" onClick={() => notificationsApi.markAllRead().then(load)}>
          Mark all read
        </button>
      </div>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
        In-app, SMS & WhatsApp-style alerts for orders, payments, and deliveries.
      </p>

      {items.length === 0 ? (
        <p className="empty-state">No notifications yet.</p>
      ) : (
        items.map((n) => (
          <div
            key={n.id}
            className="card"
            style={{
              marginBottom: '0.5rem',
              opacity: n.is_read ? 0.7 : 1,
              borderLeft: n.is_read ? undefined : '3px solid var(--primary)',
            }}
            onClick={() => !n.is_read && notificationsApi.markRead(n.id).then(load)}
          >
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'start' }}>
              <span>{channelIcon(n.channel)}</span>
              <div>
                <strong>{n.title}</strong>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{n.body}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
