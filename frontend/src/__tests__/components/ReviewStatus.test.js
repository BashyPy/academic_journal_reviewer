import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import ReviewStatus from '../../components/ReviewStatus';

jest.mock('axios');
const mockedAxios = axios;

describe('ReviewStatus Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    mockedAxios.get.mockImplementationOnce(() => new Promise(() => {}));
    
    render(<ReviewStatus submissionId="test-id" />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('displays review status and tasks', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        status: 'processing',
        tasks: [
          { agent_type: 'methodology', status: 'completed' },
          { agent_type: 'literature', status: 'running' },
          { agent_type: 'clarity', status: 'pending' },
          { agent_type: 'ethics', status: 'pending' }
        ]
      }
    });

    render(<ReviewStatus submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/review status/i)).toBeInTheDocument();
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
      expect(screen.getByText(/methodology/i)).toBeInTheDocument();
      expect(screen.getByText(/literature/i)).toBeInTheDocument();
      expect(screen.getByText(/clarity/i)).toBeInTheDocument();
      expect(screen.getByText(/ethics/i)).toBeInTheDocument();
    });
  });

  test('shows completed status', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        status: 'completed',
        tasks: [
          { agent_type: 'methodology', status: 'completed' },
          { agent_type: 'literature', status: 'completed' },
          { agent_type: 'clarity', status: 'completed' },
          { agent_type: 'ethics', status: 'completed' }
        ]
      }
    });

    render(<ReviewStatus submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/review is complete/i)).toBeInTheDocument();
      expect(screen.getByText('Status: completed')).toBeInTheDocument();
    });
  });

  test('handles API error', async () => {
    mockedAxios.get.mockRejectedValueOnce({
      response: {
        data: { detail: 'Submission not found' }
      }
    });

    render(<ReviewStatus submissionId="invalid-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
      expect(screen.getByText(/submission not found/i)).toBeInTheDocument();
    });
  });

  test('auto-refreshes status', async () => {
    jest.useFakeTimers();
    
    mockedAxios.get
      .mockResolvedValueOnce({
        data: { status: 'processing', tasks: [] }
      })
      .mockResolvedValueOnce({
        data: { status: 'completed', tasks: [] }
      });

    render(<ReviewStatus submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });
    
    // Fast-forward time to trigger refresh
    jest.advanceTimersByTime(5000);
    
    await waitFor(() => {
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });
    
    jest.useRealTimers();
  });

  test('displays task progress indicators', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        status: 'processing',
        tasks: [
          { agent_type: 'methodology', status: 'completed' },
          { agent_type: 'literature', status: 'running' },
          { agent_type: 'clarity', status: 'pending' },
          { agent_type: 'ethics', status: 'failed' }
        ]
      }
    });

    render(<ReviewStatus submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/✓/)).toBeInTheDocument(); // completed
      expect(screen.getByText(/⏳/)).toBeInTheDocument(); // running
      expect(screen.getByText(/⏸/)).toBeInTheDocument(); // pending
      expect(screen.getByText(/❌/)).toBeInTheDocument(); // failed
    });
  });
});