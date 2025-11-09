import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

// Mock child components
jest.mock('../components/UploadForm', () => {
  return function MockUploadForm({ onUploadSuccess }) {
    return (
      <div data-testid="upload-form">
        <button onClick={() => onUploadSuccess('test-id-123')}>
          Mock Upload Success
        </button>
      </div>
    );
  };
});

jest.mock('../components/ReviewStatus', () => {
  return function MockReviewStatus({ submissionId }) {
    return <div data-testid="review-status">Status for {submissionId}</div>;
  };
});

jest.mock('../components/ReviewReport', () => {
  return function MockReviewReport({ submissionId }) {
    return <div data-testid="review-report">Report for {submissionId}</div>;
  };
});

describe('App Component', () => {
  test('renders main header', () => {
    render(<App />);
    expect(screen.getByText('AARIS - Academic Journal Reviewer')).toBeInTheDocument();
    expect(screen.getByText('Agentic AI System for Academic Paper Review')).toBeInTheDocument();
  });

  test('shows upload form by default', () => {
    render(<App />);
    expect(screen.getByTestId('upload-form')).toBeInTheDocument();
    expect(screen.getByText('Upload Manuscript')).toBeInTheDocument();
  });

  test('navigation buttons appear after successful upload', () => {
    render(<App />);

    // Initially only upload button should be visible
    expect(screen.getByText('Upload Manuscript')).toBeInTheDocument();
    expect(screen.queryByText('Review Status')).not.toBeInTheDocument();
    expect(screen.queryByText('Final Report')).not.toBeInTheDocument();

    // Simulate successful upload
    fireEvent.click(screen.getByText('Mock Upload Success'));

    // Now all navigation buttons should be visible
    expect(screen.getByText('Upload Manuscript')).toBeInTheDocument();
    expect(screen.getByText('Review Status')).toBeInTheDocument();
    expect(screen.getByText('Final Report')).toBeInTheDocument();
  });

  test('switches to status view after upload', () => {
    render(<App />);

    // Simulate successful upload
    fireEvent.click(screen.getByText('Mock Upload Success'));

    // Should switch to status view
    expect(screen.getByTestId('review-status')).toBeInTheDocument();
    expect(screen.getByText('Status for test-id-123')).toBeInTheDocument();
  });

  test('navigation between views works', () => {
    render(<App />);

    // Upload a file first
    fireEvent.click(screen.getByText('Mock Upload Success'));

    // Should be on status view
    expect(screen.getByTestId('review-status')).toBeInTheDocument();

    // Click on Final Report
    fireEvent.click(screen.getByText('Final Report'));
    expect(screen.getByTestId('review-report')).toBeInTheDocument();
    expect(screen.getByText('Report for test-id-123')).toBeInTheDocument();

    // Click back to Upload
    fireEvent.click(screen.getByText('Upload Manuscript'));
    expect(screen.getByTestId('upload-form')).toBeInTheDocument();
  });

  test('active navigation button has correct class', () => {
    render(<App />);

    // Upload button should be active initially
    const uploadButton = screen.getByText('Upload Manuscript');
    expect(uploadButton).toHaveClass('active');

    // Upload a file
    fireEvent.click(screen.getByText('Mock Upload Success'));

    // Status button should be active now
    const statusButton = screen.getByText('Review Status');
    expect(statusButton).toHaveClass('active');
    expect(uploadButton).not.toHaveClass('active');
  });
});
