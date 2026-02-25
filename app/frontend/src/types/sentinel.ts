export type PublisherStatus =
  | 'Trusted'
  | 'Watchlist'
  | 'Suspicious'
  | 'Zero Conversions'
  | 'Bot-Like Activity';

export interface PublisherRow {
  id: string;
  name: string;
  trustScore: number;
  ctr: number;          // percentage value, e.g. 1.2 means 1.2%
  cvr: number;          // percentage value
  anomalyScore: number; // 0.0 – 1.0
  status: PublisherStatus;
  lastAlert: string;    // human-readable, e.g. "2h ago" or "—"
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

export interface MiniPieSegment {
  value: number;
  color: string;
  label?: string;
}
