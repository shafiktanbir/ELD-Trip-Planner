import { useState } from 'react';
import Layout from './components/Layout/Layout';
import TripForm from './components/TripForm/TripForm';
import MapView from './components/MapView/MapView';
import ELDLogSheet from './components/ELDLogSheet/ELDLogSheet';
import TripSummary from './components/TripSummary/TripSummary';
import Toast from './components/Toast/Toast';
import { planTrip } from './services/api';
import './App.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type, id: Date.now() });
  };

  const handlePlanTrip = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const data = await planTrip(formData);
      setTripData(data);
      const days = data.daily_logs?.length || 1;
      const miles = data.summary?.total_miles?.toFixed(0) || '?';
      showToast(`✅ Route planned! ${miles} miles across ${days} ELD log day${days > 1 ? 's' : ''}.`, 'success');
    } catch (err) {
      const message = err.response?.data?.error || err.message || 'Failed to plan trip. Please try again.';
      setError(message);
      showToast(message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setTripData(null);
    setError(null);
  };

  return (
    <Layout>
      <div className="app-content">
        {/* Left Panel — Form + Summary */}
        <aside className="app-sidebar">
          <TripForm
            onSubmit={handlePlanTrip}
            loading={loading}
            onReset={handleReset}
            hasResults={!!tripData}
          />
          {error && (
            <div className="error-card glass-card fade-in" id="error-message">
              <div className="error-icon">⚠️</div>
              <p className="error-text">{error}</p>
              <button className="error-dismiss" onClick={() => setError(null)}>
                Dismiss
              </button>
            </div>
          )}
          {tripData && <TripSummary data={tripData} />}
        </aside>

        {/* Main Content — Map + ELD Logs */}
        <main className="app-main">
          {!tripData && !loading && (
            <div className="empty-state slide-up">
              <div className="empty-state-icon">🚛</div>
              <h2>Plan Your Trip</h2>
              <p>Enter your trip details to generate an HOS-compliant route with ELD daily log sheets.</p>
              <div className="empty-state-features">
                <div className="feature-item">
                  <span className="feature-icon">🗺️</span>
                  <span>Interactive route map</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">📋</span>
                  <span>FMCSA-compliant ELD logs</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⏱️</span>
                  <span>HOS break &amp; rest planning</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⛽</span>
                  <span>Fuel stop scheduling</span>
                </div>
              </div>
              <div className="empty-state-rules">
                <h3>FMCSA Rules Applied</h3>
                <div className="rules-grid">
                  <div className="rule-pill">11-Hr Driving Limit</div>
                  <div className="rule-pill">14-Hr Window</div>
                  <div className="rule-pill">30-Min Break @ 8h</div>
                  <div className="rule-pill">10-Hr Off-Duty Reset</div>
                  <div className="rule-pill">70-Hr / 8-Day Cycle</div>
                  <div className="rule-pill">1,000-Mi Fueling</div>
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="loading-overlay slide-up" id="loading-indicator">
              <div className="loading-truck">
                <span className="loading-truck-icon">🚛</span>
                <div className="loading-road">
                  <div className="loading-dashes" />
                </div>
              </div>
              <p className="loading-title">Calculating your HOS-compliant route...</p>
              <p className="text-muted">Geocoding locations → routing → HOS engine → ELD logs</p>
              <div className="loading-steps">
                <span className="step step--active">🌍 Geocoding</span>
                <span className="step-arrow">→</span>
                <span className="step step--active">🗺️ Routing</span>
                <span className="step-arrow">→</span>
                <span className="step step--active">⏱️ HOS</span>
                <span className="step-arrow">→</span>
                <span className="step step--active">📋 ELD</span>
              </div>
            </div>
          )}

          {tripData && (
            <div className="results-container fade-in">
              <section className="map-section" id="map-section">
                <h3 className="section-title">
                  <span className="section-icon">🗺️</span>
                  Route &amp; Stops
                </h3>
                <MapView data={tripData} />
              </section>

              <section className="eld-section" id="eld-section">
                <div className="eld-section-header">
                  <h3 className="section-title">
                    <span className="section-icon">📋</span>
                    Daily ELD Log Sheets
                  </h3>
                  <button
                    className="btn btn-secondary print-btn"
                    id="print-eld-btn"
                    onClick={() => window.print()}
                    title="Print ELD Log Sheets"
                  >
                    🖨️ Print Logs
                  </button>
                </div>
                <div className="eld-logs-container">
                  {tripData.daily_logs && tripData.daily_logs.map((log, index) => (
                    <ELDLogSheet key={log.date} log={log} index={index} />
                  ))}
                </div>
              </section>
            </div>
          )}
        </main>
      </div>

      {/* Toast notifications */}
      {toast && (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </Layout>
  );
}

export default App;
