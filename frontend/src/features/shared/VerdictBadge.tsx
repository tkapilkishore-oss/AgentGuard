import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldAlert, Clock } from 'lucide-react';

interface VerdictBadgeProps {
  decision?: 'ALLOW' | 'ESCALATE' | 'DENY' | string | null;
  status?: string | null;
  reasonCode?: string | null;
  size?: 'sm' | 'md' | 'lg';
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  decision,
  status,
  reasonCode,
  size = 'md',
}) => {
  const normStatus = (status || '').toUpperCase();
  const normDecision = (decision || '').toUpperCase();

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-0.5 space-x-1',
    md: 'text-xs px-3 py-1 space-x-1.5',
    lg: 'text-sm px-4 py-1.5 space-x-2',
  }[size];

  if (normStatus === 'SUCCESS' || normDecision === 'SUCCESS') {
    return (
      <span className={`inline-flex items-center font-inter font-semibold bg-[#F0FDF4] text-verified border border-[#BBF7D0] rounded-full shadow-sm ${sizeClasses}`}>
        <CheckCircle2 className="w-3.5 h-3.5 text-verified" />
        <span>Success (Captured)</span>
      </span>
    );
  }

  if (normDecision === 'ALLOW' || normStatus === 'ALLOWED') {
    return (
      <span className={`inline-flex items-center font-inter font-semibold bg-[#F0FDF4] text-verified border border-[#BBF7D0] rounded-full shadow-sm ${sizeClasses}`}>
        <CheckCircle2 className="w-3.5 h-3.5 text-verified" />
        <span>Allowed</span>
      </span>
    );
  }

  if (normDecision === 'ESCALATE' || normStatus === 'ESCALATED') {
    return (
      <span className={`inline-flex items-center font-inter font-semibold bg-[#FEF3C7] text-escalation border border-[#FDE68A] rounded-full shadow-sm ${sizeClasses}`}>
        <AlertTriangle className="w-3.5 h-3.5 text-escalation" />
        <span>Escalated</span>
      </span>
    );
  }

  if (normDecision === 'DENY' || normStatus === 'DENIED' || normStatus === 'FAILED' || normStatus === 'REVOKED' || normStatus === 'EXPIRED') {
    return (
      <span className={`inline-flex items-center font-inter font-semibold bg-error-container/40 text-denied border border-error-container rounded-full shadow-sm ${sizeClasses}`}>
        <ShieldAlert className="w-3.5 h-3.5 text-denied" />
        <span>{reasonCode || normStatus || 'Denied'}</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center font-inter font-medium bg-surface-container text-on-surface-variant border border-surface-container-high rounded-full ${sizeClasses}`}>
      <Clock className="w-3.5 h-3.5 text-outline" />
      <span>{normDecision || normStatus || 'Ready'}</span>
    </span>
  );
};
