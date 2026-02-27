import { useState } from 'react';
import Sidebar from '../components/Sidebar';
import TimeSeriesChart from '../components/TimeSeriesChart';
import type { AnomalyEvent } from '../components/AnomalyArea';

export class Publisher {
    name: string;
    campaign: Campaign;

    constructor(name: string, campaign: Campaign) {
        this.name = name;
        this.campaign = campaign;
    }
}

export class Campaign {
  name: string;
  publishers: Publisher[];

  constructor(name: string, publishers: string[]) {
    this.name = name;
    this.publishers = publishers.map((x) => new Publisher(x, this));
  }
}

const CAMPAIGNS: Campaign[] = [
    new Campaign("Campaign Alpha", ['SPY', 'CAT']),
    new Campaign("Campaign Beta", ['DOG', 'OWL', 'FOX']),
];

// --- RNG utilities ---

function normalSample(mean: number, stddev: number): number {
  // Box-Muller transform
  const u1 = Math.random();
  const u2 = Math.random();
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return mean + stddev * z;
}

function poissonSample(lambda: number): number {
  // Knuth algorithm
  const L = Math.exp(-lambda);
  let k = 0;
  let p = 1;
  do {
    k++;
    p *= Math.random();
  } while (p > L);
  return k - 1;
}

function uniform(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

// --- State machine data generation ---

export interface DataPoint {
  x: number;
  impressions: number;
  clicks: number;
  conversions: number;
}

interface PublisherData {
  data: DataPoint[];
  anomalies: AnomalyEvent[];
}

function generatePublisherData(steps = 100): PublisherData {
  const data: DataPoint[] = [];
  const anomalies: AnomalyEvent[] = [];

  let state: 'normal' | 'abnormal' = 'normal';
  let anomalyStart: number | null = null;

  for (let i = 0; i < steps; i++) {
    // Track entry into abnormal period
    if (state === 'abnormal' && anomalyStart === null) {
      anomalyStart = i;
    }

    // Sample base values
    let impressions = poissonSample(10);
    const clickPct = Math.max(0, Math.min(1, normalSample(0.5, 0.2)));
    const convPct  = Math.max(0, Math.min(1, normalSample(0.5, 0.2)));
    let clicks      = clickPct * impressions;
    let conversions = convPct  * clicks;

    if (state === 'abnormal') {
      const choice = Math.floor(Math.random() * 3);
      if (choice === 0) {
        // Impressions spike
        impressions *= uniform(1.25, 2);
      } else if (choice === 1) {
        // Clicks pushed toward impressions
        clicks += (impressions - clicks) * uniform(0.5, 0.8);
      } else {
        // Conversions pushed toward clicks
        conversions += (clicks - conversions) * uniform(0.5, 0.8);
      }
    }

    data.push({
      x: i,
      impressions: Math.round(impressions),
      clicks:      Math.round(clicks),
      conversions: Math.round(conversions),
    });

    // State transition
    if (state === 'normal') {
      if (Math.random() < 0.1) {
        state = 'abnormal';
      }
    } else {
      if (Math.random() < 0.5) {
        // Close the current anomaly period
        anomalies.push({ x1: anomalyStart!, x2: i });
        anomalyStart = null;
        state = 'normal';
      }
    }
  }

  // Close any open anomaly at the end of the series
  if (state === 'abnormal' && anomalyStart !== null) {
    anomalies.push({ x1: anomalyStart, x2: steps - 1 });
  }

  return { data, anomalies };
}

// Pre-generate data once per publisher at module load time
const PUBLISHER_DATA = new Map<string, PublisherData>(
  CAMPAIGNS.flatMap(c => c.publishers).map(p => [p.name, generatePublisherData()])
);

function Dashboard() {
  const [selectedPublisher, setSelectedPublisher] = useState(CAMPAIGNS[0].publishers[0]);

  const { data, anomalies } = PUBLISHER_DATA.get(selectedPublisher.name)!;

  return (
    <>
      <Sidebar
        campaigns={CAMPAIGNS}
        selected={selectedPublisher}
        onSelect={setSelectedPublisher}
      />
      <div className="with-sidebar">
        <div className="main-content">
            <div>
                <h1 className="project-title">{selectedPublisher.campaign.name + " // " + selectedPublisher.name}</h1>
                <p className="subtitle">Synthetic time-series data — state-machine simulation</p>
            </div>

          <div className="panel">
            <TimeSeriesChart
              data={data}
              publisher={selectedPublisher.name}
              anomalies={anomalies}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
