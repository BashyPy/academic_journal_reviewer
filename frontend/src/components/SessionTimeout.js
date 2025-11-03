import React, { useState, useEffect } from 'react';
import authService from '../services/authService';

const SessionTimeout = ({ timeout = 30 * 60 * 1000, warningTime = 5 * 60 * 1000 }) => {
  const [showWarning, setShowWarning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    if (!authService.isAuthenticated()) return;

    let warningTimer, logoutTimer, countdownInterval;
    
    const resetTimers = () => {
      clearTimeout(warningTimer);
      clearTimeout(logoutTimer);
      clearInterval(countdownInterval);
      
      warningTimer = setTimeout(() => {
        setShowWarning(true);
        setTimeLeft(warningTime);
        countdownInterval = setInterval(() => {
          setTimeLeft(prev => {
            if (prev <= 1000) {
              clearInterval(countdownInterval);
              return 0;
            }
            return prev - 1000;
          });
        }, 1000);
      }, timeout - warningTime);
      
      logoutTimer = setTimeout(() => {
        authService.logout();
        window.location.href = '/login';
      }, timeout);
    };

    const handleActivity = () => {
      if (showWarning) setShowWarning(false);
      resetTimers();
    };

    resetTimers();
    ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
      document.addEventListener(event, handleActivity);
    });

    return () => {
      clearTimeout(warningTimer);
      clearTimeout(logoutTimer);
      clearInterval(countdownInterval);
      ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
        document.removeEventListener(event, handleActivity);
      });
    };
  }, [timeout, warningTime, showWarning]);

  if (!showWarning) return null;

  const minutes = Math.floor(timeLeft / 60000);
  const seconds = Math.floor((timeLeft % 60000) / 1000);

  return (
    <div className="session-timeout-overlay">
      <div className="session-timeout-modal">
        <h3>⏰ Session Expiring Soon</h3>
        <p>Your session will expire in {minutes}:{seconds.toString().padStart(2, '0')}</p>
        <p>Click anywhere to stay logged in.</p>
      </div>
    </div>
  );
};

export default SessionTimeout;
