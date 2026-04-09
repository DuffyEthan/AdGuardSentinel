export type PublisherStatus =
  | 'Trusted'
  | 'Watchlist'
  | 'CTR Fraud'
  | 'Impression Fraud'
  | 'Click Injection'
  | 'Fraud';

export interface PublisherRow {
  id: string;
  name: string;
  campaignId: string | null;
  campaignName: string | null;
  trustScore: number;
  ctr: number;          // percentage value, e.g. 1.2 means 1.2%
  cvr: number;          // percentage value
  anomalyScore: number; // 0.0 – 1.0
  status: PublisherStatus;
  selected?: boolean;
}

export interface TrustBucket {
  range: string;  // e.g. "0–20"
  count: number;
}

export interface FraudEvent {
  day: string;    // e.g. "Wed"
  events: number;
}

export interface ChatMessage {
  role: 'assistant' | 'user';
  content: string;
  bullets?: string[];
  isWarning?: boolean;
}

export interface PublisherOverview {
  trusted: number;    // count or percentage
  watchlist: number;
  fraudulent: number;
}
