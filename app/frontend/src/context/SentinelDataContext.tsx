import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import type { PublisherRow, PublisherStatus } from '../types/sentinel';

const API_BASE = 'http://localhost:8000';
const POLL_MS = 5000;

interface ApiSentinelPublisher {
  publisher_id: string;
  publisher_name: string;
  trust_score: number;
  anomaly_score: number;
  ctr: number;
  cvr: number;
  fraud_type: string | null;
}

interface ApiPublisher {
  publisher_id: string;
  publisher_name: string;
  campaign_id: string | null;
  campaign_name: string | null;
}

function computeStatus(
  trustScore: number,
  fraudType: string | null,
  anomalyScore: number,
  prevFraudType: string | null,
): PublisherStatus {
  if (trustScore >= 60) return 'Trusted';
  if (trustScore >= 40) return 'Watchlist';
  const effectiveFraudType =
    trustScore < 40 && anomalyScore > 40 && prevFraudType ? prevFraudType : fraudType;
  if (effectiveFraudType === 'ctr_fraud') return 'CTR Fraud';
  if (effectiveFraudType === 'impression_fraud') return 'Impression Fraud';
  if (effectiveFraudType === 'click_injection') return 'Click Injection';
  return 'Fraud';
}

interface SentinelDataContextType {
  publishers: PublisherRow[];
}

const SentinelDataContext = createContext<SentinelDataContextType | undefined>(undefined);

export function SentinelDataProvider({ children }: { children: ReactNode }) {
  const [publishers, setPublishers] = useState<PublisherRow[]>([]);
  // Campaign info is stable — fetch once and keep in a map keyed by publisher_id.
  const [campaignInfo, setCampaignInfo] = useState<Map<string, { campaignId: string | null; campaignName: string | null }>>(new Map());
  // Last known specific fraud type per publisher, for status continuity.
  const prevFraudTypes = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    fetch(`${API_BASE}/publishers`)
      .then(r => r.json())
      .then((pubs: ApiPublisher[]) => {
        const map = new Map<string, { campaignId: string | null; campaignName: string | null }>();
        for (const p of pubs) {
          map.set(p.publisher_id, { campaignId: p.campaign_id, campaignName: p.campaign_name });
        }
        setCampaignInfo(map);
      })
      .catch(() => {});
  }, []);

  const fetchPublishers = useCallback(() => {
    fetch(`${API_BASE}/sentinel/publishers`)
      .then(r => r.json())
      .then((data: ApiSentinelPublisher[]) => {
        setPublishers(data.map(p => {
          const campaign = campaignInfo.get(p.publisher_id);
          return {
            id: p.publisher_id,
            name: p.publisher_name,
            campaignId: campaign?.campaignId ?? null,
            campaignName: campaign?.campaignName ?? null,
            trustScore: p.trust_score,
            anomalyScore: p.anomaly_score,
            ctr: p.ctr,
            cvr: p.cvr,
            status: (() => {
            const prev = prevFraudTypes.current.get(p.publisher_id) ?? null;
            if (p.fraud_type && p.fraud_type !== 'none') {
              prevFraudTypes.current.set(p.publisher_id, p.fraud_type);
            }
            return computeStatus(p.trust_score, p.fraud_type, p.anomaly_score, prev);
          })(),
          };
        }));
      })
      .catch(() => {});
  }, [campaignInfo]);

  useEffect(() => {
    fetchPublishers();
    const id = setInterval(fetchPublishers, POLL_MS);
    return () => clearInterval(id);
  }, [fetchPublishers]);

  return (
    <SentinelDataContext.Provider value={{ publishers }}>
      {children}
    </SentinelDataContext.Provider>
  );
}

export function useSentinelData() {
  const ctx = useContext(SentinelDataContext);
  if (!ctx) throw new Error('useSentinelData must be used within SentinelDataProvider');
  return ctx;
}
