import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ReviewReport({ submissionId }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await axios.get(`/api/v1/submissions/${submissionId}/report`);
        setReport(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch report');
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [submissionId]);

  if (loading) return <div className="loading">Loading report...</div>;
  if (error) return <div className="error">{error}</div>;

  const formatMarkdown = (text) => {
    return text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/\n/gim, '<br>');
  };

  return (
    <div className="report-container">
      <h2>Final Review Report</h2>
      <p><strong>Manuscript:</strong> {report.title}</p>
      <p><strong>Completed:</strong> {new Date(report.completed_at).toLocaleString()}</p>
      
      <div className="report-content">
        <div dangerouslySetInnerHTML={{ __html: formatMarkdown(report.final_report) }} />
      </div>
      
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <button 
          onClick={() => {
            const element = document.createElement('a');
            const file = new Blob([report.final_report], { type: 'text/markdown' });
            element.href = URL.createObjectURL(file);
            element.download = `review_report_${submissionId}.md`;
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
          }}
          style={{
            background: '#3498db',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Download Report
        </button>
      </div>
    </div>
  );
}

export default ReviewReport;