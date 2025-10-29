import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ReviewReport({ submissionId }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/v1/submissions/${submissionId}/report`);
        console.log('Report response:', response.data); // Debug log
        setReport(response.data);
      } catch (err) {
        console.error('Report fetch error:', err); // Debug log
        setError(err.response?.data?.detail || 'Failed to fetch report');
      } finally {
        setLoading(false);
      }
    };

    if (submissionId) {
      fetchReport();
    }
  }, [submissionId]);

  if (loading) return <div className="loading">Loading report...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!report) return <div className="error">No report data available</div>;

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/v1/submissions/${submissionId}/download`, {
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
      console.error('PDF download error:', err); // Debug log
      setError('Failed to download PDF report');
    }
  };

  // Convert markdown-style content to HTML for better display
  const formatReportContent = (content) => {
    if (!content) return '';
    
    return content
      .replace(/^## (.*$)/gim, '<h3>$1</h3>')
      .replace(/^# (.*$)/gim, '<h2>$1</h2>')
      .replace(/^\*\*(.*)\*\*$/gim, '<strong>$1</strong>')
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="report-container">
      <h2>Final Review Report</h2>
      <p><strong>Manuscript:</strong> {report.title || 'Unknown'}</p>
      <p><strong>Completed:</strong> {report.completed_at ? new Date(report.completed_at).toLocaleString() : 'Unknown'}</p>
      
      {report.final_report ? (
        <div className="report-content" style={{
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          margin: '20px 0',
          maxHeight: '600px',
          overflowY: 'auto',
          border: '1px solid #dee2e6'
        }}>
          <h3>Review Summary</h3>
          <div 
            dangerouslySetInnerHTML={{ 
              __html: formatReportContent(report.final_report) 
            }}
            style={{
              lineHeight: '1.6',
              fontSize: '14px'
            }}
          />
        </div>
      ) : (
        <div className="report-content" style={{
          background: '#fff3cd',
          padding: '20px',
          borderRadius: '8px',
          margin: '20px 0',
          border: '1px solid #ffeaa7',
          textAlign: 'center'
        }}>
          <h3>Report Content Not Available</h3>
          <p>The review report content is not yet available or may not have been generated properly.</p>
          <p>Please try refreshing the page or contact support if the issue persists.</p>
        </div>
      )}
      
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <button 
          onClick={downloadPDF}
          style={{
            background: '#3498db',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Download PDF Report
        </button>
      </div>
      
      {report.disclaimer && (
        <div style={{
          background: '#fff3cd',
          border: '1px solid #ffeaa7',
          borderRadius: '5px',
          padding: '15px',
          marginTop: '20px',
          fontSize: '14px'
        }}>
          <strong>⚠️ Disclaimer:</strong> {report.disclaimer}
        </div>
      )}
    </div>
  );
}

export default ReviewReport;