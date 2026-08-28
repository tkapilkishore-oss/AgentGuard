import React from 'react';
import { Bot, Cpu, User, CreditCard } from 'lucide-react';

interface ActorBadgeProps {
  actor: string;
}

export const ActorBadge: React.FC<ActorBadgeProps> = ({ actor }) => {
  const norm = (actor || '').toLowerCase();

  switch (norm) {
    case 'agent':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-inter font-medium bg-error-container/30 text-error border border-error-container">
          <Bot className="w-3 h-3 text-error" />
          <span>Agent (Untrusted)</span>
        </span>
      );
    case 'firewall':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-inter font-medium bg-lavender-tint text-[#4C1D95] border border-primary-fixed">
          <Cpu className="w-3 h-3 text-primary-container" />
          <span>Firewall (Authoritative)</span>
        </span>
      );
    case 'human':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-inter font-medium bg-secondary-fixed text-secondary-on-container border border-secondary-container">
          <User className="w-3 h-3 text-secondary" />
          <span>Human Approver</span>
        </span>
      );
    case 'razorpay':
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-inter font-medium bg-emerald-50 text-verified border border-emerald-200">
          <CreditCard className="w-3 h-3 text-verified" />
          <span>Razorpay Gateway</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-inter font-medium bg-surface-container text-on-surface-variant border border-surface-container-high">
          <User className="w-3 h-3" />
          <span>{actor}</span>
        </span>
      );
  }
};
