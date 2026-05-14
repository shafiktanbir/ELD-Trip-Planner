import { useState } from 'react';
import Layout from './components/Layout/Layout';
import TripForm from './components/TripForm/TripForm';
import MapView from './components/MapView/MapView';
import ELDLogSheet from './components/ELDLogSheet/ELDLogSheet';
import TripSummary from './components/TripSummary/TripSummary';
import { planTrip } from './services/api';
import './App.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePlanTrip = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const data = await planTrip(formData);
      setTripData(data);
    } catch (err) {
      const message = err.response?.data?.error || err.message || 'Failed to plan trip. Please try again.';
      setError(message);
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
                  <span>HOS break & rest planning</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⛽</span>
                  <span>Fuel stop scheduling</span>
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="loading-overlay slide-up">
              <div className="spinner" />
              <p>Calculating your HOS-compliant route...</p>
              <p className="text-muted">This may take a few seconds</p>
            </div>
          )}

          {tripData && (
            <div className="results-container fade-in">
              <section className="map-section" id="map-section">
                <h3 className="section-title">
                  <span className="section-icon">🗺️</span>
                  Route & Stops
                </h3>
                <MapView data={tripData} />
              </section>

              <section className="eld-section" id="eld-section">
                <h3 className="section-title">
                  <span className="section-icon">📋</span>
                  Daily ELD Log Sheets
                </h3>
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
    </Layout>
  );
}

export default App;
