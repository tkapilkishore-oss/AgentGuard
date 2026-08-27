import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Play,
  UserCheck,
  UserX,
  Lock,
  Database,
  CreditCard,
  FileCode,
} from 'lucide-react';

import { api, ProposeResponseData, ExecuteResponseData } from '../../lib/api';

interface DecisionTraceProps {
  currentTransaction: ProposeResponseData | null;
  agentClaim?: {
    product_id: string;
    claimed_price: string;
    quantity: number;
  };
  onTransactionUpdated: (updatedResult: any) => void;
  onRefreshMandate: () => void;
}

export const DecisionTrace: React.FC<DecisionTraceProps> = ({
  currentTransaction,
  agentClaim,
  onTransactionUpdated,
  onRefreshMandate,
}) => {
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<ExecuteResponseData | null>(null);
  const [approving, setApproving] = useState(false);

  if (!currentTransaction) {
    return (
      <div className="flex flex-col items-center justify-center h-full glass-panel rounded-xl border border-slate-800 p-8 text-center">
        <div className="p-4 bg-slate-900 rounded-full text-slate-600 mb-4 border border-slate-800">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h3 className="text-sm font-semibold text-slate-300">No Active Decision Trace</h3>
        <p className="text-xs text-slate-500 max-w-xs mt-1">
          Propose a transaction using the Shopping Agent or Attack Console to inspect the side-by-side authorization trace.
        </p>
      </div>
    );
  }

  const claimedPrice = agentClaim ? parseFloat(agentClaim.claimed_price) : 0;
  const authoritativeTotal = typeof currentTransaction.authoritative_total === 'number'
    ? currentTransaction.authoritative_total
    : parseFloat(currentTransaction.authoritative_total || '0');
  const priceMismatch = agentClaim && claimedPrice !== authoritativeTotal;

  const handleExecute = async () => {
    setExecuting(true);
    try {
      const { envelope } = await api.executeTransaction({
        transaction_id: currentTransaction.transaction_id,
      });
      if (envelope.data) {
        setExecuteResult(envelope.data);
        onTransactionUpdated({
          ...currentTransaction,
          execute_result: envelope.data,
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setExecuting(false);
      onRefreshMandate();
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      const { envelope } = await api.approveTransaction(currentTransaction.transaction_id);
      if (envelope.success) {
        onTransactionUpdated({
          ...currentTransaction,
          decision: 'ALLOW',
          reason_code: 'APPROVED_BY_HUMAN',
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setApproving(false);
      onRefreshMandate();
    }
  };

  const handleReject = async () => {
    setApproving(true);
    try {
      const { envelope } = await api.rejectTransaction(currentTransaction.transaction_id);
      if (envelope.success) {
        onTransactionUpdated({
          ...currentTransaction,
          decision: 'DENY',
          reason_code: 'REJECTED_BY_HUMAN',
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setApproving(false);
      onRefreshMandate();
    }
  };

  // Verdict Styling
  const getVerdictBadge = () => {
    if (executeResult?.status === 'success') {
      return (
        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>STATUS: SUCCESS (PAYMENT CAPTURED)</span>
        </span>
      );
    }

    switch (currentTransaction.decision) {
      case 'ALLOW':
        return (
          <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>VERDICT: ALLOWED</span>
          </span>
        );
      case 'ESCALATE':
        return (
          <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>VERDICT: ESCALATED (REQUIRES APPROVAL)</span>
          </span>
        );
      case 'DENY':
      default:
        return (
          <span className="px-3 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/30 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>VERDICT: DENIED</span>
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden border border-slate-800 shadow-2xl p-4 space-y-4 overflow-y-auto">
      {/* Top Banner */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>Decision Trace Panel</span>
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            ID: {currentTransaction.transaction_id.substring(0, 18)}...
          </p>
        </div>
        {getVerdictBadge()}
      </div>

      {/* Canonical Reason Code */}
      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
        <div className="text-xs font-mono text-slate-400">Canonical Reason Code:</div>
        <div className="font-mono text-xs font-bold px-2.5 py-1 bg-slate-900 border border-slate-700 rounded text-indigo-300">
          {executeResult ? executeResult.reason_code : currentTransaction.reason_code}
        </div>
      </div>

      {/* Pipeline Verification Stage Stepper */}
      <div className="grid grid-cols-4 gap-2 text-center text-[10px] font-mono">
        <div className="p-2 bg-slate-900/90 rounded border border-indigo-500/30 text-indigo-300">
          <FileCode className="w-3.5 h-3.5 mx-auto mb-1 text-indigo-400" />
          <span>1. PROPOSE</span>
        </div>
        <div className="p-2 bg-slate-900/90 rounded border border-indigo-500/30 text-indigo-300">
          <Database className="w-3.5 h-3.5 mx-auto mb-1 text-indigo-400" />
          <span>2. VERIFY</span>
        </div>
        <div
          className={`p-2 rounded border ${
            currentTransaction.decision === 'ALLOW'
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : currentTransaction.decision === 'ESCALATE'
              ? 'bg-amber-950/40 border-amber-500/40 text-amber-300'
              : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 mx-auto mb-1" />
          <span>3. POLICY</span>
        </div>
        <div
          className={`p-2 rounded border ${
            executeResult?.status === 'success'
              ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300 font-bold'
              : 'bg-slate-950 border-slate-800 text-slate-600'
          }`}
        >
          <CreditCard className="w-3.5 h-3.5 mx-auto mb-1" />
          <span>4. EXECUTE</span>
        </div>
      </div>

      {/* "LLM Lies" Visual Side-by-Side Comparison Box */}
      <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-200 border-b border-slate-800/80 pb-2">
          <span>Decision Trace: Claimed vs Authoritative Truth</span>
          {priceMismatch && (
            <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded text-[10px] font-mono animate-pulse">
              PRICE MISMATCH DETECTED
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 font-mono text-xs">
          {/* Agent Claim Column */}
          <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-2">
            <div className="text-[10px] text-slate-400 uppercase font-sans font-medium flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Untrusted Agent Claim</span>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400 text-[11px]">Claimed Price:</div>
              <div className={`font-bold text-sm ${priceMismatch ? 'text-rose-400 underline decoration-rose-500 decoration-wavy' : 'text-slate-200'}`}>
                ₹{agentClaim ? parseFloat(agentClaim.claimed_price).toLocaleString('en-IN') : 'N/A'}
              </div>
            </div>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
              Quantity: {agentClaim?.quantity || 1}
            </div>
          </div>

          {/* Server Authoritative Truth Column */}
          <div className="p-3 bg-indigo-950/20 rounded-lg border border-indigo-500/30 space-y-2">
            <div className="text-[10px] text-indigo-400 uppercase font-sans font-medium flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>Server Catalog Truth</span>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400 text-[11px]">Authoritative Price:</div>
              <div className="font-bold text-sm text-emerald-400">
                ₹{authoritativeTotal.toLocaleString('en-IN')}
              </div>
            </div>
            <div className="text-[10px] text-indigo-300/80 pt-1 border-t border-indigo-500/20">
              Re-derived from Postgres DB
            </div>
          </div>
        </div>
      </div>

      {/* Human Escalation Resolution Box (if ESCALATED) */}
      {currentTransaction.decision === 'ESCALATE' && (
        <div className="p-3.5 bg-amber-950/20 border border-amber-500/30 rounded-xl space-y-2">
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold">
            <AlertTriangle className="w-4 h-4" />
            <span>Human Approver Action Required</span>
          </div>
          <p className="text-[11px] text-slate-300">
            This transaction exceeds the mandate's standard budget limit. A human operator can explicitly authorize or reject it.
          </p>
          <div className="flex items-center space-x-2 pt-1">
            <button
              onClick={handleApprove}
              disabled={approving}
              className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center space-x-1"
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Approve Over-Budget</span>
            </button>
            <button
              onClick={handleReject}
              disabled={approving}
              className="flex-1 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center space-x-1"
            >
              <UserX className="w-3.5 h-3.5" />
              <span>Reject Request</span>
            </button>
          </div>
        </div>
      )}

      {/* Payment Execution Controls (if ALLOWED or APPROVED) */}
      {currentTransaction.decision === 'ALLOW' && executeResult?.status !== 'success' && (
        <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-400">
            <span>Authorized for Execution</span>
            <Lock className="w-3.5 h-3.5" />
          </div>
          <p className="text-[11px] text-slate-300">
            Firewall policies passed. Execute payment through Razorpay test-mode API.
          </p>
          <button
            onClick={handleExecute}
            disabled={executing}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-all flex items-center justify-center space-x-1.5 shadow-lg shadow-emerald-900/30"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{executing ? 'Executing Razorpay Payment...' : 'Execute Payment via Razorpay'}</span>
          </button>
        </div>
      )}

      {/* Execution Result Log */}
      {executeResult && (
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-1 text-slate-300">
          <div className="text-[10px] text-slate-500 uppercase">Razorpay Execution Result</div>
          <div className="flex justify-between">
            <span className="text-slate-400">Status:</span>
            <span className={executeResult.status === 'success' ? 'text-emerald-400' : 'text-rose-400'}>
              {executeResult.status}
            </span>
          </div>
          {executeResult.razorpay_payment_id && (
            <div className="flex justify-between">
              <span className="text-slate-400">Payment ID:</span>
              <span className="text-indigo-300">{executeResult.razorpay_payment_id}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
