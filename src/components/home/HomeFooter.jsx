export default function HomeFooter({ onResearcherAccess }) {
  return (
    <footer className="home-footer">
      <div className="home-footer__inner">
        <span>NeuroCortex research project website</span>
        <button type="button" className="home-btn" style={{ fontSize: 12, padding: '8px 12px' }} onClick={onResearcherAccess}>
          Researcher access
        </button>
      </div>
    </footer>
  );
}
