import { useState, useMemo, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSentinelData } from '../context/SentinelDataContext';
import StatCard from '../components/sentinel/StatCard';
import PublisherTable from '../components/sentinel/PublisherTable';
import TrustDistributionChart from '../components/sentinel/TrustDistributionChart';
import PublisherOverviewChart from '../components/sentinel/PublisherOverviewChart';
import SentinelAssistant from '../components/sentinel/SentinelAssistant';
import type {
  PublisherRow,
  TrustBucket,
  FraudEvent,
  ChatMessage,
  PublisherOverview,
} from '../types/sentinel';

const API_BASE = 'http://localhost:8000';

/* ── Demo context data (sent to Gemini as ML log context) ────────────── */

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

function SentinelDashboard() {
  const navigate = useNavigate();
  const { publishers } = useSentinelData();

  // Default to the first publisher once loaded
  const [selectedPublisher, setSelectedPublisher] = useState('');
  useEffect(() => {
    if (publishers.length > 0 && !selectedPublisher) {
      setSelectedPublisher(publishers[0].name);
    }
  }, [publishers, selectedPublisher]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'I can help answer questions about publishers and their trust scores.' },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  /* ── Derived stats ──────────────────────────────────────────────────── */

  const publishersMonitored = publishers.length;
  const suspiciousPublishers = useMemo(
    () => publishers.filter(p => p.status !== 'Trusted').length,
    [publishers]
  );
  const avgNetworkCtr = useMemo(() => {
    if (publishers.length === 0) return 0;
    const sum = publishers.reduce((acc, p) => acc + p.ctr, 0);
    return Math.round((sum / publishers.length) * 10) / 10;
  }, [publishers]);
  const overview: PublisherOverview = useMemo(() => ({
    trusted:    publishers.filter(p => p.status === 'Trusted').length,
    watchlist:  publishers.filter(p => p.status === 'Watchlist').length,
    fraudulent: publishers.filter(p => p.status !== 'Trusted' && p.status !== 'Watchlist').length,
  }), [publishers]);

  const computedTrustBuckets: TrustBucket[] = useMemo(() => {
    const buckets: TrustBucket[] = [
      { range: '0–20',   count: 0 },
      { range: '20–40',  count: 0 },
      { range: '40–60',  count: 0 },
      { range: '60–80',  count: 0 },
      { range: '80–90',  count: 0 },
      { range: '90–100', count: 0 },
    ];
    for (const p of publishers) {
      const s = p.trustScore;
      if      (s < 20)  buckets[0].count++;
      else if (s < 40)  buckets[1].count++;
      else if (s < 60)  buckets[2].count++;
      else if (s < 80)  buckets[3].count++;
      else if (s < 90)  buckets[4].count++;
      else              buckets[5].count++;
    }
    return buckets;
  }, [publishers]);

  /* ── Helpers ────────────────────────────────────────────────────────── */

  /** Find the publisher UUID for the currently selected name. */
  const getSelectedPublisherId = useCallback((): string | null => {
    const pub = publishers.find(p => p.name === selectedPublisher);
    return pub?.id ?? null;
  }, [publishers, selectedPublisher]);

  /** Build the context object to send alongside every Gemini request. */
  const buildContext = useCallback(() => ({
    trust_buckets: DEMO_TRUST_BUCKETS,
    fraud_events: DEMO_FRAUD_EVENTS,
    publishers: publishers.map(p => ({
      name: p.name,
      trustScore: p.trustScore,
      ctr: p.ctr,
      cvr: p.cvr,
      status: p.status,
      anomalyScore: p.anomalyScore,
    })),
  }), [publishers]);

  /** Call the backend chat endpoint and append the response. */
  const sendToGemini = useCallback(async (
    userMessage: string,
    action?: string,
  ) => {
    const publisherId = getSelectedPublisherId();

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/sentinel/assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          context: buildContext(),
          history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
          action: action ?? null,
          publisher_id: publisherId,
        }),
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }

      const data = await res.json();

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant' as const,
          content: data.content || 'No response received.',
          bullets: data.bullets?.length ? data.bullets : undefined,
          isWarning: data.isWarning ?? false,
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant' as const,
          content: `Sorry, I couldn't get a response. ${err instanceof Error ? err.message : 'Unknown error'}`,
          isWarning: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [getSelectedPublisherId, buildContext, messages]);

  /* ── Event handlers ─────────────────────────────────────────────────── */

  function handleShowDetails(_pub: PublisherRow) {
    navigate('/publishers');
  }

  function handleExplainTrust() {
    sendToGemini(`Explain trust score for ${selectedPublisher}`, 'explain');
  }

  function handleShowAnomalies() {
    sendToGemini(`Show anomalies & evidence for ${selectedPublisher}`, 'evidence');
  }

  function handleCompareNetwork() {
    sendToGemini(`Compare ${selectedPublisher} against the network`, 'compare');
  }

  function handleSendMessage(text: string) {
    sendToGemini(text);
  }

  /* ── Render ─────────────────────────────────────────────────────────── */

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
      </div>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div className="sentinel-main">
        {/* Left column */}
        <div className="sentinel-left">
          <PublisherTable onShowDetails={handleShowDetails} />
          <div className="sentinel-charts-row">
            <TrustDistributionChart data={computedTrustBuckets} />
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
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

export default SentinelDashboard;
