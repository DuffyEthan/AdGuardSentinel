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

const DEMO_ANOMALIES: AnomalyEvent[] = [
  { x1: 40, x2: 60 },
];

// Generate synthetic data: f(x) = 2 + sin(10x)
function generateData(): { x: number; y: number }[] {
  const data = [];
  for (let i = 0; i < 100; i++) {
    const x = (i / 99) * 100;
    const y = 8 + 2*Math.sin(10 * x);
    const y2 = 4.5 + Math.sin(15 * (x+0.1));
    const y3 = 2 + 0.5*Math.sin(16 * (x+0.4));
    data.push({ x, y, y2, y3 });
  }
  return data;
}

function Dashboard() {
  
  const [selectedPublisher, setSelectedPublisher] = useState(CAMPAIGNS[0].publishers[0]);
  const data = generateData();

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
                <p className="subtitle">Synthetic time-series data: f(x) = 2 + sin(10x)</p>
            </div>

          <div className="panel">
            <TimeSeriesChart
              data={data}
              publisher={selectedPublisher.name}
              anomalies={DEMO_ANOMALIES}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
