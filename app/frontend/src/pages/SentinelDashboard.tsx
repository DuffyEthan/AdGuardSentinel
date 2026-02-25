import { useState } from 'react';
import StatCard from '../components/sentinel/StatCard';
import MiniPieChart from '../components/sentinel/MiniPieChart';
import PublisherTable from '../components/sentinel/PublisherTable';
import TrustDistributionChart from '../components/sentinel/TrustDistributionChart';
import FraudEventsChart from '../components/sentinel/FraudEventsChart';
import PublisherOverviewChart from '../components/sentinel/PublisherOverviewChart';
import SentinelAssistant from '../components/sentinel/SentinelAssistant';
import type {
  PublisherRow,
  TrustBucket,
  FraudEvent,
  ChatMessage,
  PublisherOverview,
  MiniPieSegment,
} from '../types/sentinel';

// ─── Demo / placeholder data ────────────────────────────────────────────────
// Replace these with real API props when connecting to the backend.

const DEMO_PUBLISHERS: PublisherRow[] = [
  { id: '1', name: 'Site_A', trustScore: 91, ctr: 1.2, cvr: 3.2, anomalyScore: 0.08, status: 'Trusted',          lastAlert: '—' },
  { id: '2', name: 'Site_B', trustScore: 58, ctr: 2.8, cvr: 1.1, anomalyScore: 0.48, status: 'Watchlist',         lastAlert: '4h ago' },
  { id: '3', name: 'Site_C', trustScore: 33, ctr: 8.3, cvr: 0.3, anomalyScore: 0.81, status: 'Suspicious',        lastAlert: '1h ago' },
  { id: '4', name: 'Site_D', trustScore: 20, ctr: 7.6, cvr: 0.1, anomalyScore: 0.92, status: 'Zero Conversions',  lastAlert: '30m ago' },
  { id: '5', name: 'Site_E', trustScore: 12, ctr: 9.1, cvr: 0.2, anomalyScore: 0.96, status: 'Bot-Like Activity', lastAlert: '10m ago' },
];

const DEMO_TRUST_BUCKETS: TrustBucket[] = [
  { range: '0–20',   count: 42 },
  { range: '20–40',  count: 31 },
  { range: '40–60',  count: 20 },
  { range: '60–80',  count: 18 },
  { range: '80–90',  count: 14 },
  { range: '90–100', count: 25 },
];

const DEMO_FRAUD_EVENTS: FraudEvent[] = [
  { day: 'Wed', events: 9 },
  { day: 'Thu', events: 11 },
  { day: 'Fri', events: 14 },
  { day: 'Sat', events: 12 },
  { day: 'Sun', events: 17 },
  { day: 'Mon', events: 15 },
  { day: 'Tue', events: 19 },
];

const DEMO_OVERVIEW: PublisherOverview = { trusted: 77, watchlist: 7, fraudulent: 16 };

const DEMO_MINI_PIE: MiniPieSegment[] = [
  { value: 78, color: '#4caf50', label: '78%' },
  { value: 77, color: '#ffc107', label: '77%' },
  { value: 22, color: '#e53935' },
];

const DEMO_INIT_MESSAGES: ChatMessage[] = [
  {
    role: 'assistant',
    content: 'I can help answer questions about publishers and their trust scores.',
  },
  {
    role: 'user',
    content: 'Explain trust score for Site_C',
  },
  {
    role: 'assistant',
    content: 'Explain trust score for Site_C:',
    isWarning: true,
    bullets: [
      'A large CTR spike detected without matching conversion increase',
      'CTR: 8.9% vs baseline 1.5%',
      'CVR: 0.4% vs baseline 2.1% (recent drop).',
      'Consistent, stable impression volume patterns in the 4h.',
    ],
  },
];
// ────────────────────────────────────────────────────────────────────────────

export interface SentinelDashboardProps {
  /** Summary stats shown in the top bar */
  publishersMonitored?: number;
  suspiciousPublishers?: number;
  avgNetworkCtr?: number;
  fraudEventsLast24h?: number;
  miniPieSegments?: MiniPieSegment[];
  /** Table data */
  publishers?: PublisherRow[];
  /** Charts data */
  trustBuckets?: TrustBucket[];
  fraudEvents?: FraudEvent[];
  /** Right-column data */
  overview?: PublisherOverview;
}

function SentinelDashboard({
  publishersMonitored  = 150,
  suspiciousPublishers = 12,
  avgNetworkCtr        = 1.9,
  fraudEventsLast24h   = 17,
  miniPieSegments      = DEMO_MINI_PIE,
  publishers           = DEMO_PUBLISHERS,
  trustBuckets         = DEMO_TRUST_BUCKETS,
  fraudEvents          = DEMO_FRAUD_EVENTS,
  overview             = DEMO_OVERVIEW,
}: SentinelDashboardProps) {
  const [sortBy, setSortBy]                       = useState('trustScore');
  const [selectedPublisher, setSelectedPublisher] = useState(publishers[0]?.name ?? '');
  const [messages, setMessages]                   = useState<ChatMessage[]>(DEMO_INIT_MESSAGES);

  // Sort publishers client-side; backend can also pre-sort via props
  const sortedPublishers = [...publishers].sort((a, b) => {
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    const aVal = a[sortBy as keyof PublisherRow] as number;
    const bVal = b[sortBy as keyof PublisherRow] as number;
    return bVal - aVal;
  });

  function handleShowDetails(pub: PublisherRow) {
    console.log('Show details for', pub.name);
  }

  function handleExplainTrust() {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: `Explain trust score for ${selectedPublisher}` },
      {
        role: 'assistant',
        content: `Explain trust score for ${selectedPublisher}:`,
        isWarning: true,
        bullets: ['Connect the backend to populate this explanation.'],
      },
    ]);
  }

  function handleShowAnomalies() {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: `Show anomalies & evidence for ${selectedPublisher}` },
      { role: 'assistant', content: 'Connect the backend to populate anomaly evidence.' },
    ]);
  }

  function handleCompareNetwork() {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: `Compare ${selectedPublisher} against network` },
      { role: 'assistant', content: 'Connect the backend to populate network comparison.' },
    ]);
  }

  function handleSendMessage(text: string) {
    setMessages(prev => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: 'Connect the backend to answer this question.' },
    ]);
  }

  return (
    <div className="main-content sentinel-page">
      <h1 className="sentinel-page__title">
        AdGuard Sentinel: <span className="sentinel-page__subtitle">Publisher Trust Dashboard</span>
      </h1>

      {/* ── Stats row ─────────────────────────────────────────────────────── */}
      <div className="sentinel-stats-row">
        <StatCard label="Publishers Monitored"   value={publishersMonitored}  variant="teal" />
        <StatCard label="Suspicious Publishers"  value={suspiciousPublishers} variant="orange" />
        <StatCard label="Avg Network CTR"        value={`${avgNetworkCtr}%`}  variant="orange" />
        <StatCard label="Fraud Events (Last 24h)" value={fraudEventsLast24h}  variant="red" />
        <div className="stat-card stat-card--mini-pie">
          <MiniPieChart segments={miniPieSegments} size={90} />
        </div>
      </div>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div className="sentinel-main">
        {/* Left column */}
        <div className="sentinel-left">
          <PublisherTable
            publishers={sortedPublishers}
            sortBy={sortBy}
            onSortChange={setSortBy}
            onShowDetails={handleShowDetails}
          />
          <div className="sentinel-charts-row">
            <TrustDistributionChart data={trustBuckets} />
            <FraudEventsChart data={fraudEvents} />
          </div>
        </div>

        {/* Right column */}
        <div className="sentinel-right">
          <PublisherOverviewChart overview={overview} />
          <SentinelAssistant
            publishers={publishers.map(p => p.name)}
            selectedPublisher={selectedPublisher}
            onPublisherChange={setSelectedPublisher}
            onExplainTrust={handleExplainTrust}
            onShowAnomalies={handleShowAnomalies}
            onCompareNetwork={handleCompareNetwork}
            messages={messages}
            onSendMessage={handleSendMessage}
          />
        </div>
      </div>
    </div>
  );
}

export default SentinelDashboard;
