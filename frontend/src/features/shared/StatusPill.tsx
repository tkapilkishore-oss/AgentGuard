import React from 'react';

interface StatusPillProps {
  label: string;
  value: string;
  status?: 'online' | 'offline' | 'active' | 'warning' | 'info';
  icon?: React.ReactNode;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  label,
  value,
  status = 'info',
  icon,
}) => {
  const statusClasses = {
    online: 'text-verified font-semibold',
    offline: 'text-denied font-semibold',
    active: 'text-secondary font-semibold',
    warning: 'text-escalation font-semibold',
    info: 'text-primary font-semibold',
  }[status];

  return (
    <div className="flex items-center space-x-1.5 px-3 py-1 bg-surface-container-lowest/90 rounded-full border border-surface-container text-xs font-inter shadow-sm">
      {icon && <span className="text-on-surface-variant">{icon}</span>}
      <span className="text-on-surface-variant/80 font-medium">{label}:</span>
      <span className={statusClasses}>{value}</span>
    </div>
  );
};
