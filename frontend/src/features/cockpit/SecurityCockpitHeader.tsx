import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Shield,
  History,
  Zap,
  Mic,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const SecurityCockpitHeader: React.FC = () => {
  const location = useLocation();
  const {
    mandate,
    isConversationalOpen,
    setIsConversationalOpen,
    loadingAction,
    revokeMandate,
  } = useAgentGuard();

  const navItems = [
    { path: '/live', label: 'Live Protection', icon: <Shield className="w-4 h-4" /> },
    { path: '/threats', label: 'Threat Lab', icon: <Zap className="w-4 h-4" /> },
    { path: '/forensics', label: 'Forensic Ledger', icon: <History className="w-4 h-4" /> },
  ];

  // Authoritative server-derived budget calculation with non-negative guard
  const rawBudgetRemaining = mandate ? parseFloat(mandate.budget_remaining) : 3000;
  const budgetRemaining = Math.max(0, isNaN(rawBudgetRemaining) ? 0 : rawBudgetRemaining);
  const rawBudgetTotal = mandate ? parseFloat(mandate.budget_total) : 3000;
  const budgetTotal = Math.max(0, isNaN(rawBudgetTotal) ? 3000 : rawBudgetTotal);
  const budgetPercentage = Math.max(0, Math.min(100, (budgetRemaining / (budgetTotal || 1)) * 100));

  return (
    <header className="sticky top-3.5 z-50 w-full px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto flex justify-center">
      {/* Centered, Fully Contained Rounded Navigation Bar with Balanced Margins */}
      <nav className="w-full min-h-[58px] flex items-center justify-between px-3.5 sm:px-5 md:px-6 py-2 rounded-full bg-white/95 backdrop-blur-md shadow-[0px_4px_30px_rgba(43,0,102,0.07)] border border-surface-container-high transition-all">
        {/* Left: Brand Name & Icon */}
        <Link
          to="/"
          className="flex items-center gap-2.5 sm:gap-3 group focus:outline-none flex-shrink-0"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-primary flex items-center justify-center text-white shadow-sm ring-4 ring-lavender-tint group-hover:scale-105 transition-transform flex-shrink-0">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-outfit font-extrabold text-base sm:text-lg text-primary tracking-tight">
            AgentGuard
          </span>
        </Link>

        {/* Center: Primary Product Navigation Tabs */}
        <div className="flex items-center gap-1 bg-surface-container-low p-1 rounded-full border border-surface-container flex-shrink-0">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`py-1.5 px-2.5 sm:px-3.5 rounded-full text-xs sm:text-sm font-inter transition-all duration-200 flex items-center gap-1.5 whitespace-nowrap ${
                  isActive
                    ? 'text-primary font-bold bg-white shadow-sm border border-surface-container-high'
                    : 'text-on-surface-variant font-medium hover:text-primary hover:bg-white/60'
                }`}
              >
                {item.icon}
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Right: Authoritative Budget Status, Revoke Button & Talk to AgentGuard CTA */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* Authoritative Mandate Budget Status */}
          {mandate && (
            <div
              data-agent-target="cockpit-budget"
              className="hidden sm:flex items-center gap-2 px-3 py-1 bg-surface-container-low rounded-full border border-surface-container text-xs font-inter flex-shrink-0"
            >
              <span className="text-on-surface-variant text-[11px] font-medium">Budget:</span>
              <span className="font-bold text-verified font-mono">
                ₹{budgetRemaining.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
              </span>
              <div className="w-10 xl:w-12 bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    budgetPercentage > 40 ? 'bg-verified' : budgetPercentage > 15 ? 'bg-escalation' : 'bg-denied'
                  }`}
                  style={{ width: `${budgetPercentage}%` }}
                />
              </div>
              {mandate.status === 'active' ? (
                <button
                  onClick={revokeMandate}
                  disabled={loadingAction}
                  className="ml-0.5 px-2 py-0.5 bg-error-container/60 hover:bg-error-container text-error rounded-full text-[10px] font-bold font-inter transition-colors"
                  title="Revoke Mandate"
                >
                  Revoke
                </button>
              ) : (
                <span className="px-2 py-0.5 bg-error-container text-error rounded-full text-[10px] font-bold font-inter">
                  Revoked
                </span>
              )}
            </div>
          )}

          {/* Talk to AgentGuard Button - Prominent & 100% Contained */}
          <button
            onClick={() => setIsConversationalOpen(!isConversationalOpen)}
            className="h-9 sm:h-10 px-3.5 sm:px-5 bg-primary hover:bg-secondary text-white rounded-full font-inter text-xs sm:text-sm font-semibold transition-all duration-300 hover:shadow-md active:scale-95 flex items-center gap-1.5 sm:gap-2 whitespace-nowrap flex-shrink-0"
          >
            <Mic className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white flex-shrink-0" />
            <span className="hidden sm:inline">Talk to AgentGuard</span>
            <span className="sm:hidden">Assistant</span>
          </button>
        </div>
      </nav>
    </header>
  );
};
