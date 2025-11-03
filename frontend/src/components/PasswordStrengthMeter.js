import React from 'react';

const PasswordStrengthMeter = ({ password }) => {
  const getStrength = () => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    return strength;
  };

  const strength = getStrength();
  const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#27ae60'];

  if (!password) return null;

  return (
    <div className="password-strength">
      <div className="strength-bar">
        <div 
          className="strength-fill" 
          style={{ width: `${(strength / 5) * 100}%`, background: colors[strength - 1] }}
        />
      </div>
      <span style={{ color: colors[strength - 1], fontSize: '12px' }}>
        {labels[strength - 1]}
      </span>
    </div>
  );
};

export default PasswordStrengthMeter;
