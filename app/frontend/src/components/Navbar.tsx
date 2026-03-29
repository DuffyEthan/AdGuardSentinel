import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

function Navbar() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <button className="navbar-btn" onClick={() => navigate('/')}>
          Sentinel
        </button>
        <button className="navbar-btn" onClick={() => navigate('/publishers')}>
          Publisher Details
        </button>
        <button className="navbar-btn" onClick={() => navigate('/dashboard')}>
          Time Series
        </button>
      </div>
      <div className="navbar-right">
        <button className="navbar-btn" onClick={toggleTheme}>
          {theme === 'light' ? 'Dark 🌙' : 'Light ☀️'}
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
