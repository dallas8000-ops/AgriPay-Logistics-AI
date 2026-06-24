import { Link } from 'react-router-dom';
import { useCapabilities } from '../context/CapabilitiesContext';
import './HonestyBanner.css';

/** Demoted integration notes — full detail lives on Settings. */
export default function HonestyBanner() {
  const caps = useCapabilities();
  if (!caps?.warnings?.length) return null;

  return (
    <footer className="honesty-footer" role="status">
      <Link to="/settings" className="honesty-footer-link">
        Integration status
      </Link>
      <span className="honesty-footer-sep">·</span>
      <span className="honesty-footer-hint">Optional channels not configured on this server</span>
    </footer>
  );
}
