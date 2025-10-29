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

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${submissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `review_report_${submissionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download PDF report');
    }
  };

  return (
    <div className="report-container">
      <h2>Final Review Report</h2>
      <p><strong>Manuscript:</strong> {report.title}</p>
      <p><strong>Completed:</strong> {new Date(report.completed_at).toLocaleString()}</p>
      
      <div className="report-content">
        <p>Your comprehensive review report is ready for download as a PDF.</p>
        <p><strong>Status:</strong> {report.status}</p>
      </div>
      
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <button 
          onClick={downloadPDF}
          style={{
            background: '#3498db',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Download PDF Report
        </button>
      </div>
    </div>
  );
}

export default ReviewReport;