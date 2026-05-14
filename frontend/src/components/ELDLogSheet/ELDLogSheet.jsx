import { useEffect, useRef } from 'react';
import './ELDLogSheet.css';

/**
 * ELD Log Sheet — Canvas-rendered daily log grid matching FMCSA format.
 *
 * The grid has:
 * - 4 status rows: Off Duty, Sleeper Berth, Driving, On Duty (Not Driving)
 * - 24 hour columns (midnight to midnight)
 * - 15-minute subdivisions
 * - Status lines drawn horizontally in the appropriate row
 * - Vertical transitions between status changes
 */

const STATUS_LABELS = ['Off Duty', 'Sleeper\nBerth', 'Driving', 'On Duty\n(Not Driving)'];
const STATUS_KEYS = ['off_duty', 'sleeper_berth', 'driving', 'on_duty_not_driving'];
const STATUS_COLORS = {
  off_duty: '#94a3b8',
  sleeper_berth: '#a78bfa',
  driving: '#34d399',
  on_duty_not_driving: '#fb923c',
};

// Canvas dimensions
const CANVAS_PADDING_LEFT = 120;
const CANVAS_PADDING_RIGHT = 20;
const CANVAS_PADDING_TOP = 50;
const CANVAS_PADDING_BOTTOM = 30;
const ROW_HEIGHT = 40;
const GRID_ROWS = 4;

function ELDLogSheet({ log, index }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !log) return;

    const dpr = window.devicePixelRatio || 1;
    const displayWidth = canvas.parentElement.clientWidth || 800;
    const displayHeight = CANVAS_PADDING_TOP + (ROW_HEIGHT * GRID_ROWS) + CANVAS_PADDING_BOTTOM;

    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const gridLeft = CANVAS_PADDING_LEFT;
    const gridRight = displayWidth - CANVAS_PADDING_RIGHT;
    const gridWidth = gridRight - gridLeft;
    const gridTop = CANVAS_PADDING_TOP;
    const gridBottom = gridTop + ROW_HEIGHT * GRID_ROWS;

    // ── Clear ──
    ctx.clearRect(0, 0, displayWidth, displayHeight);

    // ── Hour columns ──
    const hourWidth = gridWidth / 24;

    // Draw header hours
    ctx.font = '600 11px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';

    for (let h = 0; h <= 24; h++) {
      const x = gridLeft + h * hourWidth;

      // Hour label (show M for midnight, N for noon)
      let label = '';
      if (h === 0 || h === 24) label = 'M';
      else if (h === 12) label = 'N';
      else if (h <= 12) label = String(h);
      else label = String(h - 12);

      ctx.fillStyle = (h === 0 || h === 12 || h === 24) ? '#818cf8' : '#64748b';
      ctx.fillText(label, x, gridTop - 8);

      // Vertical grid line
      ctx.beginPath();
      ctx.moveTo(x, gridTop);
      ctx.lineTo(x, gridBottom);
      ctx.strokeStyle = (h === 0 || h === 12 || h === 24)
        ? 'rgba(99, 102, 241, 0.3)'
        : 'rgba(100, 116, 139, 0.15)';
      ctx.lineWidth = (h === 0 || h === 12 || h === 24) ? 1.5 : 0.5;
      ctx.stroke();

      // 15-min subdivisions
      if (h < 24) {
        for (let q = 1; q < 4; q++) {
          const qx = x + q * (hourWidth / 4);
          ctx.beginPath();
          ctx.moveTo(qx, gridTop);
          ctx.lineTo(qx, gridBottom);
          ctx.strokeStyle = 'rgba(100, 116, 139, 0.07)';
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }

    // ── Row labels + horizontal lines ──
    for (let r = 0; r <= GRID_ROWS; r++) {
      const y = gridTop + r * ROW_HEIGHT;

      // Horizontal grid line
      ctx.beginPath();
      ctx.moveTo(gridLeft, y);
      ctx.lineTo(gridRight, y);
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.2)';
      ctx.lineWidth = r === 0 || r === GRID_ROWS ? 1.5 : 0.5;
      ctx.stroke();

      // Row label
      if (r < GRID_ROWS) {
        const labelY = y + ROW_HEIGHT / 2;
        const labelLines = STATUS_LABELS[r].split('\n');

        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.font = '500 10px Inter, sans-serif';
        ctx.fillStyle = STATUS_COLORS[STATUS_KEYS[r]];

        if (labelLines.length === 1) {
          ctx.fillText(labelLines[0], gridLeft - 10, labelY);
        } else {
          ctx.fillText(labelLines[0], gridLeft - 10, labelY - 7);
          ctx.fillText(labelLines[1], gridLeft - 10, labelY + 7);
        }

        // Row center dashed line (for graph drawing)
        ctx.beginPath();
        ctx.setLineDash([2, 4]);
        ctx.moveTo(gridLeft, labelY);
        ctx.lineTo(gridRight, labelY);
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.08)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    // ── Draw Status Lines ──
    if (log.segments && log.segments.length > 0) {
      const getRowY = (status) => {
        const rowIdx = STATUS_KEYS.indexOf(status);
        if (rowIdx === -1) return gridTop + ROW_HEIGHT * 0.5; // default to off_duty row center
        return gridTop + rowIdx * ROW_HEIGHT + ROW_HEIGHT / 2;
      };

      const getX = (hour) => {
        return gridLeft + (hour / 24) * gridWidth;
      };

      let prevEndY = null;
      let prevEndX = null;

      for (const seg of log.segments) {
        const startX = getX(seg.start_hour);
        const endX = getX(seg.end_hour);
        const y = getRowY(seg.status);
        const color = STATUS_COLORS[seg.status] || '#94a3b8';

        // Vertical transition from previous status
        if (prevEndY !== null && prevEndX !== null && Math.abs(prevEndY - y) > 1) {
          ctx.beginPath();
          ctx.moveTo(startX, prevEndY);
          ctx.lineTo(startX, y);
          ctx.strokeStyle = color;
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        // Horizontal status line
        ctx.beginPath();
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.stroke();

        prevEndY = y;
        prevEndX = endX;
      }
    }

  }, [log]);

  // Format date for display
  const formatDate = (dateStr) => {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatHours = (hours) => {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return `${h}h ${m}m`;
  };

  if (!log) return null;

  return (
    <div className="eld-log-sheet glass-card slide-up" style={{ animationDelay: `${index * 100}ms` }}>
      {/* Log Header */}
      <div className="log-header">
        <div className="log-date-info">
          <span className="log-day-badge">Day {log.day_number}</span>
          <h4 className="log-date">{formatDate(log.date)}</h4>
        </div>
        <div className="log-miles">
          <span className="log-miles-value">{log.total_miles?.toFixed(0) || 0}</span>
          <span className="log-miles-label">miles</span>
        </div>
      </div>

      {/* Canvas Grid */}
      <div className="log-canvas-container">
        <canvas
          ref={canvasRef}
          className="log-canvas"
          id={`eld-canvas-day-${log.day_number}`}
        />
      </div>

      {/* Status Totals */}
      <div className="log-totals">
        <div className="total-item">
          <span className="total-dot" style={{ background: STATUS_COLORS.off_duty }} />
          <span className="total-label">Off Duty</span>
          <span className="total-value">{formatHours(log.totals?.off_duty || 0)}</span>
        </div>
        <div className="total-item">
          <span className="total-dot" style={{ background: STATUS_COLORS.sleeper_berth }} />
          <span className="total-label">Sleeper</span>
          <span className="total-value">{formatHours(log.totals?.sleeper_berth || 0)}</span>
        </div>
        <div className="total-item">
          <span className="total-dot" style={{ background: STATUS_COLORS.driving }} />
          <span className="total-label">Driving</span>
          <span className="total-value">{formatHours(log.totals?.driving || 0)}</span>
        </div>
        <div className="total-item">
          <span className="total-dot" style={{ background: STATUS_COLORS.on_duty_not_driving }} />
          <span className="total-label">On Duty</span>
          <span className="total-value">{formatHours(log.totals?.on_duty_not_driving || 0)}</span>
        </div>
      </div>

      {/* Remarks */}
      {log.remarks && log.remarks.length > 0 && (
        <div className="log-remarks">
          <h5 className="remarks-title">Remarks & Conditions</h5>
          <div className="remarks-list">
            {log.remarks.map((remark, i) => (
              <div key={i} className="remark-item">
                <span className="remark-time">{remark.time}</span>
                <span className="remark-text">{remark.text}</span>
                {remark.location && (
                  <span className="remark-location">📍 {remark.location}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ELDLogSheet;
