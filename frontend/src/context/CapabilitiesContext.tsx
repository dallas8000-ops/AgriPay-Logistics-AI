import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { capabilitiesApi, type Capabilities } from '../lib/api';

const CapabilitiesContext = createContext<Capabilities | null>(null);

export function CapabilitiesProvider({ children }: { children: ReactNode }) {
  const [caps, setCaps] = useState<Capabilities | null>(null);

  useEffect(() => {
    capabilitiesApi.get().then(setCaps).catch(() => {});
  }, []);

  return (
    <CapabilitiesContext.Provider value={caps}>
      {children}
    </CapabilitiesContext.Provider>
  );
}

export function useCapabilities() {
  return useContext(CapabilitiesContext);
}

export function isAgriMode(caps: Capabilities | null) {
  return !caps || caps.product_mode === 'agri';
}

export function merchantApiLive(caps: Capabilities | null) {
  return caps?.collection.merchant_api.status === 'operational';
}

export function flutterwaveLive(caps: Capabilities | null) {
  return caps?.collection.flutterwave?.status === 'operational';
}

export function stripeLive(caps: Capabilities | null) {
  return caps?.collection.stripe.status === 'operational';
}
