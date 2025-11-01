import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ReviewStatus.css';

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
        console.error('Status fetch error:', err);
        setError(err.response?.data?.detail || 'Failed to fetch status');
      } finally {
        setLoading(false);
      }
    };

    if (submissionId) {
      fetchStatus();
      const interval = setInterval(fetchStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [submissionId]);

  const getStatusBadge = (taskStatus) => {
    const badges = {
      completed: { icon: '✅', class: 'badge-completed', text: 'Completed' },
      running: { icon: '🔄', class: 'badge-running', text: 'Running' },
      failed: { icon: '❌', class: 'badge-failed', text: 'Failed' },
      pending: { icon: '⏳', class: 'badge-pending', text: 'Pending' }
    };
    return badges[taskStatus] || badges.pending;
  };

  const getAgentName = (agentType) => {
    const names = {
      methodology: '🔬 Methodology Analysis',
      literature: '📚 Literature Review',
      clarity: '✍️ Clarity Assessment',
      ethics: '⚖️ Ethics Evaluation',
      synthesis: '🧠 Final Synthesis'
    };
    return names[agentType] || agentType;
  };

  if (loading) {
    return (
      <div className="status-container">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading review status...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="status-container">
        <div className="error">
          <h3>❌ Error Loading Status</h3>
          <p>{error}</p>
          <p><strong>Submission ID:</strong> {submissionId}</p>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="status-container">
        <div className="error">
          <h3>⚠️ No Status Data</h3>
          <p>Unable to load review status for submission {submissionId}</p>
        </div>
      </div>
    );
  }

  const overallProgress = status.tasks ? 
    Math.round((status.tasks.filter(t => t.status === 'completed').length / status.tasks.length) * 100) : 0;

  return (
    <div className="status-container">
      <h2>📊 Review Progress</h2>
      <div className="status-overview">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${overallProgress}%` }}></div>
        </div>
        <p><strong>Overall Progress:</strong> {overallProgress}% Complete</p>
        <p><strong>Submission ID:</strong> {submissionId}</p>
        <p><strong>Status:</strong> {status.status || 'Processing'}</p>
      </div>

      {status.status === 'completed' && (
        <div className="completion-notice">
          🎉 <strong>Review Complete!</strong> Your manuscript analysis is ready.
        </div>
      )}

      <div className="agents-progress">
        <h3>🤖 AI Agents Progress</h3>
        {status.tasks && status.tasks.length > 0 ? (
          status.tasks.map((task, index) => {
            const badge = getStatusBadge(task.status);
            return (
              <div key={index} className={`status-item status-${task.status}`}>
                <div className="agent-info">
                  <span className="agent-name">{getAgentName(task.agent_type)}</span>
                  <span className="agent-description">
                    {task.status === 'running' && 'Analyzing your manuscript...'}
                    {task.status === 'completed' && 'Analysis complete'}
                    {task.status === 'failed' && 'Analysis failed'}
                    {task.status === 'pending' && 'Waiting to start...'}
                  </span>
                </div>
                <div className={`status-badge ${badge.class}`}>
                  {badge.icon} {badge.text}
                </div>
              </div>
            );
          })
        ) : (
          <div className="no-tasks">
            <p>🔄 Initializing review agents...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewStatus;