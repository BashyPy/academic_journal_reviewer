import React, { useEffect } from 'react';
import axios from 'axios';
import rateLimiter from '../services/rateLimiter';

const CompletionNotification = ({ submissionId, show, onShow, onViewReport, onClose }) => {
  useEffect(() => {
    if (!submissionId) return;

    const checkCompletion = async () => {
      try {
        const response = await rateLimiter.makeRequest(`completion-${submissionId}`, () =>
          axios.get(`/api/v1/submissions/${submissionId}/report`)
        );
        if (!response.data.processing && !show) {
          onShow();
        }
      } catch (err) {
        // Ignore errors during polling
      }
    };

    const interval = setInterval(checkCompletion, 5000);
    return () => clearInterval(interval);
  }, [submissionId, show, onShow]);

  if (!show) return null;

  return (
    <div className="notification-overlay">
      <div className="notification-popup">
        <div className="notification-header">
          <h3>🎉 Review Complete!</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="notification-body">
          <p>Your manuscript analysis is ready for review.</p>
          <div className="notification-actions">
            <button className="view-report-btn" onClick={onViewReport}>
              📋 View Final Report
            </button>
            <button className="dismiss-btn" onClick={onClose}>
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompletionNotification;