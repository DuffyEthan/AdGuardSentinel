import { useNavigate } from 'react-router-dom';

function Home() {
  const navigate = useNavigate();

  return (
    <div className="main-content">
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.9fr', gap: '2rem' }}>
        <div>
          <h1 className="project-title">Project Name</h1>
          <p className="subtitle">Select an advert to view performance charts.</p>

          <div className="panel">
            <p>Welcome. This is your dashboard homepage.</p>
            <p>Click <strong>Advert A</strong> to open the publisher view.</p>
          </div>
        </div>

        <div>
          <div className="panel">
            <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>Dashboards</h2>
            <button onClick={() => navigate('/dashboard')}>
              Advert A
            </button>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '1rem' }}>
              Add more advert buttons here later.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
