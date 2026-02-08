import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TimeSeriesChart from '../components/TimeSeriesChart';
import DataTable from '../components/DataTable';

const PUBLISHERS = ['SPY', 'CAT', 'DOG', 'OWL', 'FOX'];

// Generate synthetic data: f(x) = 2 + sin(10x)
function generateData(): { x: number; y: number }[] {
  const data = [];
  for (let i = 0; i < 100; i++) {
    const x = (i / 99) * 100;
    const y = 2 + Math.sin(10 * x);
    data.push({ x, y });
  }
  return data;
}

function Dashboard() {
  const navigate = useNavigate();
  const [selectedPublisher, setSelectedPublisher] = useState(PUBLISHERS[0]);
  const data = generateData();

  return (
    <>
      <Sidebar
        publishers={PUBLISHERS}
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
            <button className="btn" onClick={() => navigate('/')}>
              ← Back to Home
            </button>
          </div>

          <div className="panel">
            <TimeSeriesChart data={data} publisher={selectedPublisher} />
            <DataTable data={data} />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
