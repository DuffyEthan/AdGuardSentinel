import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import StatCard from '../components/sentinel/StatCard';
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
} from '../types/sentinel';

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
  trustBuckets         = DEMO_TRUST_BUCKETS,
  fraudEvents          = DEMO_FRAUD_EVENTS,
  overview             = DEMO_OVERVIEW,
}: SentinelDashboardProps) {
  const navigate = useNavigate();
  const [selectedPublisher, setSelectedPublisher] = useState('');
  const [messages, setMessages]                   = useState<ChatMessage[]>(DEMO_INIT_MESSAGES);

  function handleShowDetails(_pub: PublisherRow) {
    navigate('/publishers');
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
      </div>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div className="sentinel-main">
        {/* Left column */}
        <div className="sentinel-left">
          <PublisherTable
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
          {/* <SentinelAssistant
            publishers={publishers.map(p => p.name)}
            selectedPublisher={selectedPublisher}
            onPublisherChange={setSelectedPublisher}
            onExplainTrust={handleExplainTrust}
            onShowAnomalies={handleShowAnomalies}
            onCompareNetwork={handleCompareNetwork}
            messages={messages}
            onSendMessage={handleSendMessage}
          /> */}
        </div>
      </div>
    </div>
  );
}

export default SentinelDashboard;
