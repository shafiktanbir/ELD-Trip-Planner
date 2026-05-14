import './Layout.css';

function Layout({ children }) {
  return (
    <div className="layout">
      <header className="layout-header">
        <div className="header-content">
          <div className="header-brand">
            <span className="header-logo">🚛</span>
            <div>
              <h1 className="header-title">ELD Trip Planner</h1>
              <p className="header-subtitle">FMCSA HOS-Compliant Route Planning</p>
            </div>
          </div>
          <div className="header-badge">
            <div className="pulse-dot" />
            <span>Property Carrier · 70hrs/8days</span>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

export default Layout;
