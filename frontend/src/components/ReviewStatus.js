import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ReviewStatus({ submissionId }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/v1/submissions/${submissionId}/status`);
        setStatus(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch status');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [submissionId]);

  if (loading) return <div className="loading">Loading status...</div>;
  if (error) return <div className="error">{error}</div>;

  const getStatusClass = (taskStatus) => {
    return `status-item status-${taskStatus}`;
  };

  const getStatusIcon = (taskStatus) => {
    switch (taskStatus) {
      case 'pending': return '⏳';
      case 'running': return '🔄';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  return (
    <div className="status-container">
      <h2>Review Progress</h2>
      <p>Submission ID: {submissionId}</p>
      
      <div className={getStatusClass(status.status)}>
        <span>Overall Status</span>
        <span>{getStatusIcon(status.status)} {status.status.toUpperCase()}</span>
      </div>

      <h3>Agent Tasks</h3>
      {status.tasks.map((task, index) => (
        <div key={index} className={getStatusClass(task.status)}>
          <span>{task.agent_type.charAt(0).toUpperCase() + task.agent_type.slice(1)} Agent</span>
          <span>{getStatusIcon(task.status)} {task.status.toUpperCase()}</span>
        </div>
      ))}

      {status.status === 'completed' && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#d4edda', borderRadius: '5px' }}>
          <strong>🎉 Review Complete!</strong>
          <p>Your manuscript review is ready. Click "Final Report" to view the results.</p>
        </div>
      )}
    </div>
  );
}

export default ReviewStatus;