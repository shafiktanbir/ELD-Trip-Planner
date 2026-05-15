import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

/**
 * Plan a trip — sends trip details to the backend and returns
 * route, schedule, ELD logs, and map data.
 */
export async function planTrip({ currentLocation, pickupLocation, dropoffLocation, currentCycleHours, startTime }) {
  const response = await api.post('/trips/plan/', {
    current_location: currentLocation,
    pickup_location: pickupLocation,
    dropoff_location: dropoffLocation,
    current_cycle_hours: parseFloat(currentCycleHours),
    // Convert "YYYY-MM-DDTHH:MM" (local) to ISO 8601 with timezone
    start_time: startTime ? new Date(startTime).toISOString() : undefined,
  });
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await api.get('/health/');
  return response.data;
}

export default api;
