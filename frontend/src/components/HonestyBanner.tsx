import { useCapabilities } from '../context/CapabilitiesContext';
import './HonestyBanner.css';

export default function HonestyBanner() {
  const caps = useCapabilities();
  if (!caps?.warnings?.length) return null;

  return (
    <div className="honesty-banner" role="status">
      <strong>Deployment status</strong>
      <ul>
        {caps.warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
    </div>
  );
}
