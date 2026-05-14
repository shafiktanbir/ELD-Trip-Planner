import './TripSummary.css';

function TripSummary({ data }) {
  if (!data?.summary) return null;

  const { summary, route, daily_logs, stops } = data;

  const formatHours = (hours) => {
    if (hours == null) return '—';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="trip-summary glass-card fade-in">
      <h3 className="summary-title">
        <span className="summary-icon">📊</span>
        Trip Summary
      </h3>

      {/* Route Overview */}
      <div className="summary-section">
        <h4 className="section-label">Route</h4>
        <div className="summary-grid">
          <div className="stat-item">
            <span className="stat-value stat-highlight">
              {route?.total_distance_miles?.toFixed(0) || '—'}
            </span>
            <span className="stat-label">Total Miles</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">
              {formatHours(route?.total_duration_hours)}
            </span>
            <span className="stat-label">Drive Time</span>
          </div>
        </div>
      </div>

      {/* Schedule Overview */}
      <div className="summary-section">
        <h4 className="section-label">Schedule</h4>
        <div className="summary-grid">
          <div className="stat-item">
            <span className="stat-value" style={{ color: 'var(--accent-green)' }}>
              {formatHours(summary.total_driving_hours)}
            </span>
            <span className="stat-label">Driving</span>
          </div>
          <div className="stat-item">
            <span className="stat-value" style={{ color: 'var(--accent-orange)' }}>
              {formatHours(summary.total_on_duty_hours)}
            </span>
            <span className="stat-label">On Duty</span>
          </div>
          <div className="stat-item">
            <span className="stat-value" style={{ color: 'var(--text-secondary)' }}>
              {formatHours(summary.total_off_duty_hours)}
            </span>
            <span className="stat-label">Off Duty</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">
              {formatHours(summary.total_trip_hours)}
            </span>
            <span className="stat-label">Total Trip</span>
          </div>
        </div>
      </div>

      {/* Stops */}
      <div className="summary-section">
        <h4 className="section-label">Stops & Breaks</h4>
        <div className="stops-list">
          <div className="stop-stat">
            <span className="stop-icon">⛽</span>
            <span className="stop-text">Fuel Stops</span>
            <span className="stop-count">{summary.num_fuel_stops}</span>
          </div>
          <div className="stop-stat">
            <span className="stop-icon">🛏️</span>
            <span className="stop-text">Rest Periods</span>
            <span className="stop-count">{summary.num_rest_stops}</span>
          </div>
          <div className="stop-stat">
            <span className="stop-icon">☕</span>
            <span className="stop-text">30-Min Breaks</span>
            <span className="stop-count">{summary.num_breaks}</span>
          </div>
          {summary.num_cycle_restarts > 0 && (
            <div className="stop-stat">
              <span className="stop-icon">🔄</span>
              <span className="stop-text">Cycle Restarts</span>
              <span className="stop-count">{summary.num_cycle_restarts}</span>
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="summary-section">
        <h4 className="section-label">Timeline</h4>
        <div className="timeline-info">
          <div className="timeline-item">
            <span className="timeline-label">Departure</span>
            <span className="timeline-value">{formatDate(summary.trip_start)}</span>
          </div>
          <div className="timeline-item">
            <span className="timeline-label">Arrival</span>
            <span className="timeline-value">{formatDate(summary.trip_end)}</span>
          </div>
          <div className="timeline-item">
            <span className="timeline-label">ELD Log Days</span>
            <span className="timeline-value">{daily_logs?.length || 0}</span>
          </div>
          <div className="timeline-item">
            <span className="timeline-label">Cycle Remaining</span>
            <span className="timeline-value">{formatHours(summary.cycle_hours_remaining)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TripSummary;
