import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ReviewStatus = ({ submissionId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`/api/v1/submissions/${submissionId}/status`);
        setStatus(response.data);
        setError('');
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

  const getStatusIcon = (taskStatus) => {
    switch (taskStatus) {
      case 'completed': return '✓';
      case 'running': return '⏳';
      case 'failed': return '❌';
      default: return '⏸';
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Review Status</h2>
      <p>Status: {status.status}</p>
      {status.status === 'completed' && <p>Review is complete!</p>}
      <div>
        <h3>Agent Progress:</h3>
        {status.tasks.map((task, index) => (
          <div key={index}>
            {getStatusIcon(task.status)} {task.agent_type}: {task.status}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReviewStatus;