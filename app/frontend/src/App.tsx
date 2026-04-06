import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { SentinelDataProvider } from './context/SentinelDataContext';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import SentinelDashboard from './pages/SentinelDashboard';
import PublisherDetails from './pages/PublisherDetails';
import './index.css';

function App() {
  return (
    <ThemeProvider>
      <SentinelDataProvider>
        <BrowserRouter>
          <Navbar />
          <div className="app-container">
            <Routes>
              <Route path="/" element={<SentinelDashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/dashboard/:campaign/:publisher" element={<Dashboard />} />
              <Route path="/publishers" element={<PublisherDetails />} />
            </Routes>
          </div>
        </BrowserRouter>
      </SentinelDataProvider>
    </ThemeProvider>
  );
}

export default App;
