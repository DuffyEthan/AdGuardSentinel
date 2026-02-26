import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import SentinelDashboard from './pages/SentinelDashboard';
import './index.css';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Navbar />
        <div className="app-container">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/sentinel" element={<SentinelDashboard />} />
          </Routes>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
