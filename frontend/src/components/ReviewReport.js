import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ReviewReport = ({ submissionId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await axios.get(`/api/v1/submissions/${submissionId}/report`);
        setReport(response.data);
        setError('');
      } catch (err) {
        if (err.response?.status === 400) {
          setError('Review not completed yet. Please wait...');
        } else {
          setError(err.response?.data?.detail || 'Failed to fetch report');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [submissionId]);

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${submissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${report.title}_reviewed.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const renderMarkdown = (text) => {
    return text
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/\n/gim, '<br>');
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Final Review Report</h2>
      <h3>{report.title}</h3>
      {report.completed_at && <p>Completed on: {formatDate(report.completed_at)}</p>}
      
      <div dangerouslySetInnerHTML={{ __html: renderMarkdown(report.final_report) }} />
      
      <button onClick={downloadPDF}>Download PDF</button>
      
      {report.disclaimer && (
        <div style={{ marginTop: '20px', padding: '10px', backgroundColor: '#f0f0f0' }}>
          <h4>Disclaimer</h4>
          <p>{report.disclaimer}</p>
        </div>
      )}
    </div>
  );
};

export default ReviewReport;