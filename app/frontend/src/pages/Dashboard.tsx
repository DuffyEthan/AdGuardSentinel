import { useState } from 'react';
import Sidebar from '../components/Sidebar';
import TimeSeriesChart from '../components/TimeSeriesChart';
import type { AnomalyEvent } from '../components/AnomalyArea';

export interface Campaign {
  name: string;
  publishers: string[];
}

const CAMPAIGNS: Campaign[] = [
  { name: 'Campaign Alpha', publishers: ['SPY', 'CAT'] },
  { name: 'Campaign Beta', publishers: ['DOG', 'OWL', 'FOX'] },
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
          <div className="top-bar">
            <div>
              <h1 className="project-title">{selectedPublisher}</h1>
              <p className="subtitle">Synthetic time-series data: f(x) = 2 + sin(10x)</p>
            </div>
          </div>

          <div className="panel">
            <TimeSeriesChart
              data={data}
              publisher={selectedPublisher}
              anomalies={DEMO_ANOMALIES}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
