import { useState } from 'react';
import './TripForm.css';

function TripForm({ onSubmit, loading, onReset, hasResults }) {
  const [formData, setFormData] = useState({
    currentLocation: '',
    pickupLocation: '',
    dropoffLocation: '',
    currentCycleHours: '0',
  });

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
          title="Fill with example data"
        >
          Try Example
        </button>
      </div>

      <form onSubmit={handleSubmit} className="trip-form" id="trip-form">
        <div className="form-group">
          <label className="form-label" htmlFor="currentLocation">
            <span className="label-icon">📌</span> Current Location
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

        <div className="form-group">
          <label className="form-label" htmlFor="pickupLocation">
            <span className="label-icon">📦</span> Pickup Location
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

        <div className="form-group">
          <label className="form-label" htmlFor="dropoffLocation">
            <span className="label-icon">🏁</span> Dropoff Location
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

        <div className="form-group">
          <label className="form-label" htmlFor="currentCycleHours">
            <span className="label-icon">⏱️</span> Current Cycle Used (Hours)
          </label>
          <input
            id="currentCycleHours"
            name="currentCycleHours"
            type="number"
            className="form-input"
            placeholder="0"
            min="0"
            max="70"
            step="0.5"
            value={formData.currentCycleHours}
            onChange={handleChange}
            required
            disabled={loading}
          />
          <span className="form-hint">Hours used in current 70-hr/8-day cycle (0–70)</span>
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
                Plan Trip
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
              Reset
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default TripForm;
