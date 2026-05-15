import { useEffect, useState } from 'react';
import './Toast.css';

/**
 * Toast notification component.
 * Shows a brief success/error/info notification then auto-dismisses.
 */
function Toast({ message, type = 'success', duration = 4000, onDismiss }) {
  const [visible, setVisible] = useState(true);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true);
      setTimeout(() => {
        setVisible(false);
        onDismiss?.();
      }, 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onDismiss]);

  if (!visible) return null;

  const icons = {
    success: '✅',
    error: '❌',
    info: 'ℹ️',
    warning: '⚠️',
  };

  return (
    <div className={`toast toast--${type} ${exiting ? 'toast--exiting' : 'toast--entering'}`}>
      <span className="toast__icon">{icons[type] || '📢'}</span>
      <span className="toast__message">{message}</span>
      <button
        className="toast__close"
        onClick={() => {
          setExiting(true);
          setTimeout(() => {
            setVisible(false);
            onDismiss?.();
          }, 300);
        }}
        aria-label="Dismiss notification"
      >
        ×
      </button>
    </div>
  );
}

export default Toast;
