import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { aiApi, logisticsApi, type Delivery } from '../lib/api';

export default function DeliveriesPage() {
  const { user } = useAuth();
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [drivers, setDrivers] = useState<Array<{ id: number; username: string; vehicle: string }>>([]);

  const load = () => logisticsApi.deliveries().then((r) => setDeliveries(r.results)).catch(() => {});
  useEffect(() => {
    load();
    if (user?.role === 'admin' || user?.role === 'farmer') {
      logisticsApi.availableDrivers().then(setDrivers).catch(() => {});
    }
  }, [user]);

  const assignDriver = async (deliveryId: number, driverId: number) => {
    await logisticsApi.assignDriver(deliveryId, driverId);
    load();
  };

  const updateStatus = async (id: number, status: string) => {
    await logisticsApi.updateLocation(id, { status, note: `Status updated to ${status}` });
    load();
  };

  const submitProof = async (id: number) => {
    await logisticsApi.submitProof(id, {
      recipient_name: 'Market Receiver',
      recipient_phone: '+254700000000',
      notes: 'Delivered in good condition',
    });
    load();
  };

  return (
    <div className="page">
      <h1 className="page-title">
        {user?.role === 'driver' ? 'My Delivery Jobs' : 'Delivery Tracking'}
      </h1>

      {deliveries.length === 0 ? (
        <p className="empty-state">No deliveries yet. Complete a payment to create a delivery.</p>
      ) : (
        deliveries.map((d) => (
          <div key={d.id} className="card" style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>Order #{d.order_id}</strong>
              <span className="badge">{d.status.replace('_', ' ')}</span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0.5rem 0' }}>
              📦 {d.pickup_location}<br />📍 {d.dropoff_location}
            </p>
            {d.driver_name && <p style={{ fontSize: '0.85rem' }}>Driver: {d.driver_name}</p>}
            {d.route_summary && (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                🛣️ {d.route_summary}
              </p>
            )}
            {d.tracking_events?.length > 0 && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                {d.tracking_events.slice(-3).map((e, i) => (
                  <div key={i} style={{ color: 'var(--text-muted)' }}>
                    • {e.status} — {new Date(e.timestamp).toLocaleString()}
                  </div>
                ))}
              </div>
            )}

            {(user?.role === 'admin' || user?.role === 'farmer') && d.status === 'pending' && drivers.length > 0 && (
              <select
                style={{ marginTop: '0.75rem' }}
                onChange={(e) => e.target.value && assignDriver(d.id, parseInt(e.target.value))}
                defaultValue=""
              >
                <option value="">Assign driver…</option>
                {drivers.map((dr) => (
                  <option key={dr.id} value={dr.id}>{dr.username} ({dr.vehicle})</option>
                ))}
              </select>
            )}

            {user?.role === 'driver' && d.status === 'assigned' && (
              <button className="btn btn-primary btn-block" style={{ marginTop: '0.75rem' }} onClick={() => updateStatus(d.id, 'in_transit')}>
                Start Delivery
              </button>
            )}
            {user?.role === 'driver' && d.status === 'in_transit' && (
              <button className="btn btn-primary btn-block" style={{ marginTop: '0.75rem' }} onClick={() => submitProof(d.id)}>
                Submit Proof of Delivery
              </button>
            )}

            {!d.route_summary && (
              <button
                className="btn btn-secondary btn-block"
                style={{ marginTop: '0.5rem' }}
                onClick={() => aiApi.routeSummary({ pickup: d.pickup_location, dropoff: d.dropoff_location }).then(load)}
              >
                Get route estimate
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}
