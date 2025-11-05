import React, { useState, useEffect } from 'react';
import axios from 'axios';
import rateLimiter from '../services/rateLimiter';

const ReviewReport = ({ submissionId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await rateLimiter.makeRequest(`report-${submissionId}`, () =>
          axios.get(`/api/v1/submissions/${submissionId}/report`)
        );
        const data = response.data;

        if (data.processing) {
          setProcessing(true);
          setReport(null);
        } else {
          setProcessing(false);
          setReport(data);
        }
        setError('');
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to fetch report');
        setProcessing(false);
      } finally {
        setLoading(false);
      }
    };

    if (submissionId) {
      fetchReport();

      const interval = setInterval(() => {
        if (processing || !report) {
          fetchReport();
        }
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [submissionId, processing, report]);

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${submissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Strip original extension and ensure PDF extension
      let baseTitle = report.title;
      if (baseTitle.includes('.')) {
        baseTitle = baseTitle.substring(0, baseTitle.lastIndexOf('.'));
      }
      link.setAttribute('download', `${baseTitle}_reviewed.pdf`);

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err.message || err);
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

  // Remove any HTML tags from user-provided text to prevent XSS and avoid using dangerouslySetInnerHTML
  const stripHtmlTags = (str) => {
    if (!str) return '';
    return str.replace(/<\/?[^>]+(>|$)/g, '');
  };

  const renderInline = (text, keyBase) => {
    if (!text) return '';
    const elements = [];
    let remaining = text;
    let idx = 0;
    const pattern = /(\*\*([^*]+)\*\*)|(\*([^*]+)\*)/;
    while (remaining) {
      const m = remaining.match(pattern);
      if (!m) {
        elements.push(remaining);
        break;
      }
      const index = m.index;
      if (index > 0) elements.push(remaining.slice(0, index));
      if (m[1]) elements.push(<strong key={`${keyBase}-s-${idx}`}>{m[2]}</strong>);
      else if (m[3]) elements.push(<em key={`${keyBase}-e-${idx}`}>{m[4]}</em>);
      // advance the remaining text after the matched token
      remaining = remaining.slice(index + m[0].length);
      idx++;
    }
    return elements;
  };

  const renderMarkdownElements = (text) => {
    if (!text) return null;
    // sanitize the entire markdown block to strip any HTML tags before parsing
    const safeText = stripHtmlTags(text);
    const lines = safeText.split(/\r?\n/);
    const elements = [];
    let listItems = null;
    lines.forEach((line, i) => {
      if (/^# (.*)/.test(line)) {
        const match = line.match(/^# (.*)/);
        elements.push(<h1 key={i}>{match[1]}</h1>);
      } else if (/^## (.*)/.test(line)) {
        const match = line.match(/^## (.*)/);
        elements.push(<h2 key={i}>{match[1]}</h2>);
      } else if (/^- (.*)/.test(line)) {
        const match = line.match(/^- (.*)/);
        if (!listItems) listItems = [];
        listItems.push(<li key={i}>{renderInline(match[1], i)}</li>);
      } else if (line.trim() === '') {
        if (listItems) {
          elements.push(<ul key={`ul-${i}`}>{listItems}</ul>);
          listItems = null;
        } else {
          elements.push(<br key={i} />);
        }
      } else {
        if (listItems) {
          elements.push(<ul key={`ul-${i}`}>{listItems}</ul>);
          listItems = null;
        }
        elements.push(<p key={i}>{renderInline(line, i)}</p>);
      }
    });
    if (listItems) elements.push(<ul key="ul-end">{listItems}</ul>);
    return elements;
  };

  if (loading) {
    return (
      <div className="report-container">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading review status...</p>
        </div>
      </div>
    );
  }

  if (processing) {
    return (
      <div className="report-container">
        <h2>🔄 Review in Progress</h2>
        <div className="processing-status">
          <div className="loading-spinner"></div>
          <p>Your manuscript is being analyzed by our AI agents...</p>
          <p>This process typically takes 3-5 minutes. The page will automatically update when complete.</p>
          <div className="progress-info">
            <p>📊 <strong>What's happening:</strong></p>
            <ul>
              <li>🔬 Methodology analysis</li>
              <li>📚 Literature review</li>
              <li>✍️ Clarity assessment</li>
              <li>⚖️ Ethics evaluation</li>
              <li>🧠 Final synthesis</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-container">
        <div className="error">
          <h3>❌ Error Loading Report</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="report-container">
      <h2>📋 Final Review Report</h2>
      <div className="report-header">
        <h3>{report.title}</h3>
        {report.completed_at && (
          <p className="completion-date">
            ✅ <strong>Completed:</strong> {formatDate(report.completed_at)}
          </p>
        )}
      </div>

      <div className="report-content">
        {renderMarkdownElements(report.final_report)}
      </div>

      <div className="report-actions">
        <button className="download-button" onClick={downloadPDF}>
          📄 Download PDF Report
        </button>
      </div>

      {report.disclaimer && (
        <div className="disclaimer">
          <h4>⚠️ Important Disclaimer</h4>
          <p>{report.disclaimer}</p>
        </div>
      )}
    </div>
  );
};

export default ReviewReport;
