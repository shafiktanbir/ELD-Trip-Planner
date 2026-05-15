import { useState } from 'react';
import './TripForm.css';

/** Returns a datetime-local string set to "now" for the input default */
function nowLocalString() {
  const d = new Date();
  d.setSeconds(0, 0);
  // Format: "YYYY-MM-DDTHH:MM"
  return d.toISOString().slice(0, 16);
}

function TripForm({ onSubmit, loading, onReset, hasResults }) {
  const [formData, setFormData] = useState({
    currentLocation: '',
    pickupLocation: '',
    dropoffLocation: '',
    currentCycleHours: '0',
    startTime: nowLocalString(),
  });

  const [showCycleHelp, setShowCycleHelp] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleFillExample = () => {
    setFormData({
      currentLocation: 'New York, NY',
      pickupLocation: 'Philadelphia, PA',
      dropoffLocation: 'Los Angeles, CA',
      currentCycleHours: '10',
      startTime: nowLocalString(),
    });
  };

  return (
    <div className="trip-form-card glass-card">
      <div className="form-header">
        <h3 className="form-title">
          <span className="form-title-icon">📍</span>
          Trip Details
        </h3>
        <button
          type="button"
          className="example-btn"
          onClick={handleFillExample}
          title="Fill with a sample New York → LA trip"
        >
          Try Example
        </button>
      </div>

      <form onSubmit={handleSubmit} className="trip-form" id="trip-form">

        {/* Current Location */}
        <div className="form-group">
          <label className="form-label" htmlFor="currentLocation">
            <span className="label-icon">📌</span> Where are you now?
          </label>
          <input
            id="currentLocation"
            name="currentLocation"
            type="text"
            className="form-input"
            placeholder="e.g. New York, NY"
            value={formData.currentLocation}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        {/* Pickup Location */}
        <div className="form-group">
          <label className="form-label" htmlFor="pickupLocation">
            <span className="label-icon">📦</span> Where do you pick up the load?
          </label>
          <input
            id="pickupLocation"
            name="pickupLocation"
            type="text"
            className="form-input"
            placeholder="e.g. Philadelphia, PA"
            value={formData.pickupLocation}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        {/* Dropoff Location */}
        <div className="form-group">
          <label className="form-label" htmlFor="dropoffLocation">
            <span className="label-icon">🏁</span> Where do you deliver it?
          </label>
          <input
            id="dropoffLocation"
            name="dropoffLocation"
            type="text"
            className="form-input"
            placeholder="e.g. Los Angeles, CA"
            value={formData.dropoffLocation}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        {/* Start Time */}
        <div className="form-group">
          <label className="form-label" htmlFor="startTime">
            <span className="label-icon">🕐</span> When do you start driving?
          </label>
          <input
            id="startTime"
            name="startTime"
            type="datetime-local"
            className="form-input form-input--datetime"
            value={formData.startTime}
            onChange={handleChange}
            disabled={loading}
          />
          <span className="form-hint">Defaults to right now — change if planning ahead</span>
        </div>

        {/* Cycle Hours — with help tooltip */}
        <div className="form-group">
          <label className="form-label" htmlFor="currentCycleHours">
            <span className="label-icon">⏱️</span> Hours driven this week
            <button
              type="button"
              className="help-btn"
              onClick={() => setShowCycleHelp(v => !v)}
              aria-label="Help: what is this?"
            >
              ?
            </button>
          </label>

          {showCycleHelp && (
            <div className="help-box" id="cycle-help-box">
              <strong>What is this?</strong>
              <p>
                By law, truck drivers can only work <strong>70 hours in any 8-day period</strong>.
                Enter how many hours you've already driven/worked since 8 days ago.
              </p>
              <p className="help-examples">
                <span>🟢 Just started the week → enter <strong>0</strong></span>
                <span>🟡 Worked 3 days already → enter ~<strong>30</strong></span>
                <span>🔴 Near the limit → enter <strong>60+</strong></span>
              </p>
            </div>
          )}

          <input
            id="currentCycleHours"
            name="currentCycleHours"
            type="number"
            className="form-input"
            placeholder="0"
            min="0"
            max="69"
            step="0.5"
            value={formData.currentCycleHours}
            onChange={handleChange}
            required
            disabled={loading}
          />
          <div className="cycle-bar-wrap">
            <div
              className="cycle-bar-fill"
              style={{ width: `${Math.min((parseFloat(formData.currentCycleHours) || 0) / 70 * 100, 100)}%` }}
            />
            <span className="cycle-bar-label">
              {formData.currentCycleHours || 0} / 70 hrs used
            </span>
          </div>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-lg submit-btn"
            id="plan-trip-btn"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" />
                Planning...
              </>
            ) : (
              <>
                <span>🚀</span>
                Plan My Trip
              </>
            )}
          </button>

          {hasResults && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onReset}
              disabled={loading}
            >
              New Trip
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default TripForm;
