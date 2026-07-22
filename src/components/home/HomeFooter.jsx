import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../routing/routePaths.js';

export default function HomeFooter() {
  const navigate = useNavigate();
  return (
    <footer className="home-footer">
      <div className="home-footer__inner">
        <span>NeuroCortex research project website</span>
        <button
          type="button"
          className="home-btn"
          style={{ fontSize: 12, padding: '8px 12px' }}
          onClick={() => navigate(ROUTES.researcherSignIn)}
        >
          Researcher access
        </button>
      </div>
    </footer>
  );
}
