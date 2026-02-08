import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

function Navbar() {
    const navigate = useNavigate();
    const { theme, toggleTheme } = useTheme();

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <button className="btn" onClick={() => navigate('/')}>
            Home
        </button>
        <button className="btn" onClick={() => navigate('/dashboard')}>
            Publisher Dashboard
        </button>
        <button className="btn" onClick={toggleTheme}>
            {(theme === 'light' ? 'Dark  🌙' : 'Light  ☀️')}
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
