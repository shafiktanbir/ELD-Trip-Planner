import { useEffect, useRef } from 'react';
import './MapView.css';

// We use the Leaflet JS API directly since react-leaflet requires npm install
// This component creates a Leaflet map programmatically

function MapView({ data }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    if (!data || !window.L) return;

    // Destroy previous map instance
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const L = window.L;

    // Create map
    const map = L.map(mapRef.current, {
      zoomControl: true,
      scrollWheelZoom: true,
    });

    mapInstanceRef.current = map;

    // Add tile layer (dark style)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    const bounds = [];

    // Draw route polyline
    if (data.route?.polyline && data.route.polyline.length > 0) {
      const polyline = L.polyline(data.route.polyline, {
        color: '#6366f1',
        weight: 4,
        opacity: 0.8,
        smoothFactor: 1,
      }).addTo(map);

      // Add glow effect
      L.polyline(data.route.polyline, {
        color: '#818cf8',
        weight: 8,
        opacity: 0.2,
        smoothFactor: 1,
      }).addTo(map);

      bounds.push(...data.route.polyline);
    }

    // Custom icon factory
    const createIcon = (emoji, color) => {
      return L.divIcon({
        className: 'custom-marker',
        html: `<div class="marker-pin" style="background: ${color}; box-shadow: 0 0 15px ${color}40;">
                 <span class="marker-emoji">${emoji}</span>
               </div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 40],
        popupAnchor: [0, -40],
      });
    };

    // Add waypoint markers
    if (data.route?.waypoints) {
      data.route.waypoints.forEach(wp => {
        let icon, label;
        switch (wp.type) {
          case 'origin':
            icon = createIcon('📌', '#6366f1');
            label = 'Start';
            break;
          case 'pickup':
            icon = createIcon('📦', '#22d3ee');
            label = 'Pickup';
            break;
          case 'dropoff':
            icon = createIcon('🏁', '#34d399');
            label = 'Dropoff';
            break;
          default:
            icon = createIcon('📍', '#94a3b8');
            label = wp.type;
        }

        L.marker([wp.lat, wp.lng], { icon })
          .addTo(map)
          .bindPopup(`
            <div class="map-popup">
              <strong>${label}</strong><br/>
              <span>${wp.name}</span>
            </div>
          `);

        bounds.push([wp.lat, wp.lng]);
      });
    }

    // Add stop markers
    if (data.stops) {
      data.stops.forEach(stop => {
        if (!stop.location || (stop.location[0] === 0 && stop.location[1] === 0)) return;

        let icon, label;
        switch (stop.type) {
          case 'fuel':
            icon = createIcon('⛽', '#fb923c');
            label = 'Fuel Stop';
            break;
          case 'rest':
            icon = createIcon('🛏️', '#a78bfa');
            label = 'Rest Stop';
            break;
          case 'break':
            icon = createIcon('☕', '#fbbf24');
            label = '30-Min Break';
            break;
          case 'restart':
            icon = createIcon('🔄', '#f87171');
            label = 'Cycle Restart';
            break;
          default:
            return; // Skip origin/pickup/dropoff (already shown)
        }

        const marker = L.marker(stop.location, { icon }).addTo(map);

        marker.bindPopup(`
          <div class="map-popup">
            <strong>${label}</strong><br/>
            <span>${stop.note}</span>
            ${stop.location_name ? `<br/><small>${stop.location_name}</small>` : ''}
          </div>
        `);

        bounds.push(stop.location);
      });
    }

    // Fit map to bounds
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40] });
    } else {
      map.setView([39.8283, -98.5795], 4); // Center of US
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [data]);




  return (
    <div className="map-container glass-card">
      {data?.route && (
        <div className="map-stats-bar">
          <div className="map-stat">
            <span className="map-stat-value">{data.route.total_distance_miles?.toFixed(0)} mi</span>
            <span className="map-stat-label">Total Distance</span>
          </div>
          <div className="map-stat-divider" />
          <div className="map-stat">
            <span className="map-stat-value">{data.summary?.num_fuel_stops || 0}</span>
            <span className="map-stat-label">⛽ Fuel Stops</span>
          </div>
          <div className="map-stat-divider" />
          <div className="map-stat">
            <span className="map-stat-value">{data.summary?.num_rest_stops || 0}</span>
            <span className="map-stat-label">🛏️ Rest Stops</span>
          </div>
          <div className="map-stat-divider" />
          <div className="map-stat">
            <span className="map-stat-value">{data.summary?.num_breaks || 0}</span>
            <span className="map-stat-label">☕ Breaks</span>
          </div>
        </div>
      )}
      <div ref={mapRef} className="map-element" id="trip-map" />
      {data?.route && (
        <div className="map-legend">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#6366f1' }} />
            <span>Route</span>
          </div>
          <div className="legend-item">
            <span>📌</span> <span>Start</span>
          </div>
          <div className="legend-item">
            <span>📦</span> <span>Pickup</span>
          </div>
          <div className="legend-item">
            <span>🏁</span> <span>Dropoff</span>
          </div>
          <div className="legend-item">
            <span>⛽</span> <span>Fuel</span>
          </div>
          <div className="legend-item">
            <span>🛏️</span> <span>Rest (10h)</span>
          </div>
          <div className="legend-item">
            <span>☕</span> <span>Break (30m)</span>
          </div>
          {data.summary?.num_cycle_restarts > 0 && (
            <div className="legend-item">
              <span>🔄</span> <span>Cycle Restart</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MapView;
