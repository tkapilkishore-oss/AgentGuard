import React from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Database,
  UserCheck,
  UserX,
  Play,
  Lock,
  ArrowRight,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';
import { VerdictBadge } from '../shared/VerdictBadge';

export const FirewallInspectionHero: React.FC = () => {
  const {
    activeTransaction,
    activeAgentClaim,
    activeExecutionResult,
    executeActiveTransaction,
    approveActiveTransaction,
    rejectActiveTransaction,
    loadingAction,
  } = useAgentGuard();

  if (!activeTransaction) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-white rounded-2xl border border-surface-container p-8 sm:p-12 text-center shadow-ambient-1">
        <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center text-primary mb-4 ring-8 ring-lavender-tint shadow-sm">
          <Shield className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-xl font-bold text-primary font-outfit">AgentGuard Firewall Ready</h3>
        <p className="text-sm text-on-surface-variant max-w-md mt-2 leading-relaxed font-inter">
          Submit a purchase using the Shopping Agent on the left or select a quick prompt to observe the server-authoritative boundary inspect, verify, and enforce financial invariants in real time.
        </p>
      </div>
    );
  }

  const claimedPrice = activeAgentClaim ? parseFloat(activeAgentClaim.claimed_price) : 0;
  const authoritativeTotal =
    typeof activeTransaction.authoritative_total === 'number'
      ? activeTransaction.authoritative_total
      : parseFloat(activeTransaction.authoritative_total || '0');

  const priceMismatch = activeAgentClaim && Math.abs(claimedPrice - authoritativeTotal) > 0.01;

  const currentReasonCode = activeExecutionResult
    ? activeExecutionResult.reason_code
    : activeTransaction.reason_code;

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl overflow-hidden border border-surface-container shadow-ambient-1 p-5 sm:p-6 space-y-5">
      {/* Top Banner: Authority Core + Verdict Badge */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-surface-container gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-primary flex items-center gap-2 font-outfit">
              <ShieldCheck className="w-5 h-5 text-secondary" />
              <span>Firewall Authorization Engine</span>
            </h2>
            <span className="px-2.5 py-0.5 text-xs font-inter font-semibold bg-lavender-tint text-[#4C1D95] rounded-full border border-primary-fixed">
              Server Authoritative
            </span>
          </div>
          <p className="text-xs text-on-surface-variant font-inter mt-0.5">
            Txn ID: <span className="font-mono text-primary font-medium">{activeTransaction.transaction_id.substring(0, 18)}...</span>
          </p>
        </div>

        <VerdictBadge
          decision={activeTransaction.decision}
          status={activeExecutionResult?.status}
          reasonCode={currentReasonCode}
          size="md"
        />
      </div>

      {/* 2-Column Machine Representation: Firewall Centerpiece + Authoritative Ledger Output */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-stretch">
        {/* Left Sub-Card: Firewall Scan & Decision */}
        <div className="bg-surface rounded-2xl p-5 border border-surface-container flex flex-col items-center justify-center text-center relative overflow-hidden">
          <div className="absolute top-3 right-3 flex items-center gap-1">
            {loadingAction ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-secondary" />
                <span className="text-xs font-inter font-semibold text-secondary">Verifying</span>
              </>
            ) : (
              <span className="text-xs font-inter font-medium text-on-surface-variant">Validated</span>
            )}
          </div>

          {/* Central Shield Graphic */}
          <div className="relative w-28 h-28 my-3 flex items-center justify-center">
            <div className="absolute inset-0 bg-lavender-tint rounded-full animate-ping opacity-30"></div>
            <div className="w-24 h-24 rounded-full bg-primary flex items-center justify-center text-white ring-8 ring-lavender-tint shadow-lg">
              {activeTransaction.decision === 'ALLOW' ? (
                <ShieldCheck className="w-12 h-12 text-verified" />
              ) : activeTransaction.decision === 'ESCALATE' ? (
                <AlertTriangle className="w-12 h-12 text-escalation" />
              ) : (
                <ShieldAlert className="w-12 h-12 text-error" />
              )}
            </div>
          </div>

          <h3 className="font-outfit font-bold text-primary text-base mt-1">Deterministic Policy Gate</h3>
          <p className="font-inter text-xs text-on-surface-variant mt-1 max-w-xs">
            Evaluating claimed parameters against mandate invariants & database stock.
          </p>

          <div className="mt-3 w-full pt-3 border-t border-surface-container flex items-center justify-between text-xs font-inter">
            <span className="text-on-surface-variant">Reason Code:</span>
            <span className="font-mono font-bold text-primary bg-white px-2.5 py-1 rounded-lg border border-surface-container text-[11px]">
              {currentReasonCode}
            </span>
          </div>
        </div>

        {/* Right Sub-Card: Authoritative Database Truth & Invariant Verification */}
        <div className="bg-surface rounded-2xl p-5 border border-surface-container flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-container">
              <div className="flex items-center gap-1.5 text-xs font-inter font-bold text-primary">
                <Database className="w-4 h-4 text-secondary" />
                <span>PostgreSQL Catalog Truth</span>
              </div>
              <span className="text-[11px] font-inter font-semibold text-verified bg-[#F0FDF4] px-2.5 py-0.5 rounded-full border border-[#BBF7D0]">
                Authoritative
              </span>
            </div>

            {/* Price Comparison Block */}
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className={`p-3 rounded-xl border ${priceMismatch ? 'bg-error-container/30 border-error-container text-error' : 'bg-white border-surface-container text-on-surface'}`}>
                <div className="text-[11px] text-on-surface-variant font-medium mb-1 font-inter">Claimed Price</div>
                <div className="text-base font-bold font-mono">
                  ₹{claimedPrice ? claimedPrice.toLocaleString('en-IN') : 'N/A'}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-white border border-surface-container text-primary">
                <div className="text-[11px] text-on-surface-variant font-medium mb-1 font-inter">Catalog Price</div>
                <div className="text-base font-bold font-mono text-verified">
                  ₹{authoritativeTotal.toLocaleString('en-IN')}
                </div>
              </div>
            </div>

            {priceMismatch && (
              <div className="p-2.5 bg-error-container/30 rounded-xl border border-error-container flex items-center gap-2 text-xs text-error font-inter">
                <AlertTriangle className="w-4 h-4 text-error flex-shrink-0" />
                <span>Price tampering detected: Claimed ₹{claimedPrice} ≠ Database ₹{authoritativeTotal}</span>
              </div>
            )}
          </div>

          <div className="text-xs font-inter text-on-surface-variant pt-2 border-t border-surface-container">
            <div className="flex justify-between">
              <span>Item Identifier:</span>
              <span className="font-mono font-medium text-primary">{activeAgentClaim?.product_id || 'prod-001'}</span>
            </div>
            <div className="flex justify-between mt-1">
              <span>Quantity:</span>
              <span className="font-mono font-medium text-primary">{activeAgentClaim?.quantity || 1}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Human Escalation Resolution Box (if ESCALATED) */}
      {activeTransaction.decision === 'ESCALATE' && (
        <div className="p-4 sm:p-5 bg-[#FFFBEB] border border-[#FDE68A] rounded-2xl space-y-3 shadow-sm">
          <div className="flex items-center gap-2 text-escalation text-sm font-bold font-outfit">
            <UserCheck className="w-5 h-5 text-escalation" />
            <span>Human Approver Action Required (Budget Exceeded)</span>
          </div>
          <p className="text-xs text-on-surface-variant leading-relaxed font-inter">
            This transaction exceeds the mandate's standard budget. A human supervisor can explicitly authorize this purchase or reject it. The untrusted LLM cannot override this threshold.
          </p>
          <div className="flex items-center gap-3 pt-1 font-inter">
            <button
              onClick={approveActiveTransaction}
              disabled={loadingAction}
              className="flex-1 py-2.5 bg-verified hover:bg-green-700 text-white text-xs font-semibold rounded-full transition-all flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              <UserCheck className="w-4 h-4" />
              <span>Approve Over-Budget Purchase</span>
            </button>
            <button
              onClick={rejectActiveTransaction}
              disabled={loadingAction}
              className="flex-1 py-2.5 bg-error hover:bg-red-800 text-white text-xs font-semibold rounded-full transition-all flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              <UserX className="w-4 h-4" />
              <span>Reject Proposal</span>
            </button>
          </div>
        </div>
      )}

      {/* Payment Execution Controls (if ALLOWED or APPROVED) */}
      {activeTransaction.decision === 'ALLOW' && activeExecutionResult?.status !== 'success' && (
        <div className="p-4 sm:p-5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-2xl space-y-3 shadow-sm">
          <div className="flex items-center justify-between text-xs sm:text-sm font-bold text-verified font-outfit">
            <span className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-verified" />
              <span>Authorized for Payment Execution</span>
            </span>
            <Lock className="w-4 h-4" />
          </div>
          <p className="text-xs text-on-surface-variant leading-relaxed font-inter">
            All policy invariants verified against database state. Ready to reserve budget and execute payment via Razorpay test mode.
          </p>
          <button
            onClick={() => executeActiveTransaction()}
            disabled={loadingAction}
            className="w-full py-3 bg-primary hover:bg-secondary text-white text-xs sm:text-sm font-bold rounded-full transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg disabled:opacity-50 font-inter"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{loadingAction ? 'Executing Payment via Razorpay...' : 'Execute Payment via Razorpay Gateway'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Execution Result Log Card */}
      {activeExecutionResult && (
        <div className="p-4 bg-surface rounded-2xl border border-surface-container text-xs text-on-surface space-y-2">
          <div className="flex items-center justify-between border-b border-surface-container pb-2">
            <span className="text-xs text-on-surface-variant font-semibold font-inter">Razorpay Execution Result</span>
            <span
              className={`px-2.5 py-0.5 rounded-full font-bold text-xs font-inter ${
                activeExecutionResult.status === 'success'
                  ? 'bg-[#F0FDF4] text-verified border border-[#BBF7D0]'
                  : 'bg-error-container text-error border border-error-container'
              }`}
            >
              {activeExecutionResult.status.toUpperCase()}
            </span>
          </div>
          {activeExecutionResult.razorpay_payment_id && (
            <div className="flex justify-between font-inter">
              <span className="text-on-surface-variant">Payment ID:</span>
              <span className="text-secondary font-mono font-bold">{activeExecutionResult.razorpay_payment_id}</span>
            </div>
          )}
          <div className="flex justify-between font-inter">
            <span className="text-on-surface-variant">Reason Code:</span>
            <span className="text-primary font-mono font-bold">{activeExecutionResult.reason_code}</span>
          </div>
        </div>
      )}
    </div>
  );
};
