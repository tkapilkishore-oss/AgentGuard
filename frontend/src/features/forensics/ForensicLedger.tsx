import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Copy,
  Check,
  Hash,
  FileText,
  Search,
  Cpu,
  CreditCard,
  Lock,
  Download,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';
import { VerdictBadge } from '../shared/VerdictBadge';
import { ActorBadge } from '../shared/ActorBadge';

export const ForensicLedger: React.FC = () => {
  const {
    transactions,
    selectedTxnId,
    setSelectedTxnId,
    auditData,
    fetchTransactions,
    loadingAction,
  } = useAgentGuard();

  const [filter, setFilter] = useState<'ALL' | 'SUCCESS' | 'DENIED' | 'ESCALATED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleExportJson = () => {
    if (!auditData) return;
    const blob = new Blob([JSON.stringify(auditData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-chain-${auditData.transaction.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredTransactions = transactions.filter((t) => {
    if (filter === 'SUCCESS' && t.status !== 'SUCCESS') return false;
    if (filter === 'DENIED' && t.status !== 'DENIED') return false;
    if (filter === 'ESCALATED' && t.status !== 'ESCALATED') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        t.id.toLowerCase().includes(q) ||
        (t.product_name && t.product_name.toLowerCase().includes(q)) ||
        t.reason_code.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType.toUpperCase()) {
      case 'PROPOSED':
        return <FileText className="w-4 h-4 text-error" />;
      case 'POLICY_DECISION':
        return <Cpu className="w-4 h-4 text-secondary" />;
      case 'APPROVED':
        return <CheckCircle2 className="w-4 h-4 text-verified" />;
      case 'REJECTED':
        return <XCircle className="w-4 h-4 text-denied" />;
      case 'EXECUTING':
        return <Clock className="w-4 h-4 text-secondary" />;
      case 'EXECUTED':
        return <CreditCard className="w-4 h-4 text-verified" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-denied" />;
      default:
        return <Hash className="w-4 h-4 text-outline" />;
    }
  };

  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 max-w-7xl mx-auto w-full space-y-8">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
        <div className="max-w-3xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-[#F0FDF4] border border-[#BBF7D0] text-verified px-3 py-1 rounded-full flex items-center gap-2 shadow-sm text-xs font-inter font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-verified" />
              <span>SHA-256 Chain Verified</span>
            </div>
            <div className="flex items-center gap-1.5 text-on-surface-variant font-inter text-xs bg-surface-container px-3 py-1 rounded-full">
              <div className="w-1.5 h-1.5 bg-verified rounded-full animate-pulse"></div>
              <span>PostgreSQL Synchronized</span>
            </div>
          </div>

          <h1 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary mb-3">
            Cryptographic Evidence Ledger
          </h1>
          <p className="text-on-surface-variant text-sm sm:text-base font-inter leading-relaxed">
            An immutable, reconstructable timeline of all automated financial decisions and system state changes, secured by SHA-256 cryptographic hashing.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportJson}
            disabled={!auditData}
            className="px-4 py-2 rounded-full bg-white border border-surface-container shadow-sm text-primary font-inter text-xs font-semibold hover:bg-surface-container-low transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Evidence JSON</span>
          </button>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left Column: Transaction Explorer (4 cols) */}
        <div className="lg:col-span-4 flex flex-col bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs h-[700px]">
          {/* Explorer Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block"></span>
                  Transaction Explorer
                </h2>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md border border-slate-200">
                  {transactions.length}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-inter mt-0.5">Authoritative PostgreSQL Records</p>
            </div>
            <button
              onClick={fetchTransactions}
              disabled={loadingAction}
              className="p-2 text-slate-400 hover:text-primary hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
              title="Refresh Transactions"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingAction ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Search & Filter Bar */}
          <div className="pt-3 pb-2 space-y-2.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID, product, reason..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 font-inter transition-all"
              />
            </div>

            <div className="flex gap-1 font-inter p-0.5 bg-slate-100 rounded-lg">
              {(['ALL', 'SUCCESS', 'DENIED', 'ESCALATED'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`flex-1 py-1 rounded-md text-[11px] font-mono font-semibold transition-all cursor-pointer ${
                    filter === f
                      ? 'bg-white text-primary shadow-xs font-bold'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Transaction List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 pt-1">
            {filteredTransactions.length === 0 && (
              <div className="text-center py-16 text-xs text-slate-400 font-inter">
                No transactions recorded yet. Run a proposal via Live Protection or Threat Lab.
              </div>
            )}

            {filteredTransactions.map((txn) => {
              const isSelected = txn.id === selectedTxnId;
              const amount =
                typeof txn.authoritative_total === 'number'
                  ? txn.authoritative_total.toFixed(2)
                  : parseFloat(txn.authoritative_total || '0').toFixed(2);

              return (
                <div
                  key={txn.id}
                  onClick={() => setSelectedTxnId(txn.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-slate-50/90 border-primary shadow-xs ring-1 ring-primary/20'
                      : 'bg-white border-slate-200/70 hover:bg-slate-50/60 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-xs font-bold text-slate-900">
                      {txn.id.substring(0, 8)}...{txn.id.substring(txn.id.length - 4)}
                    </span>
                    <VerdictBadge decision={txn.status} status={txn.status} reasonCode={txn.reason_code} size="sm" />
                  </div>

                  <div className="flex items-center justify-between text-xs font-inter">
                    <span className="text-slate-700 font-medium truncate max-w-[140px]">
                      {txn.product_name || txn.product_id}
                    </span>
                    <span className="font-mono font-bold text-slate-900">₹{amount}</span>
                  </div>

                  <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
                    <span className="truncate max-w-[120px]">{txn.reason_code}</span>
                    <span>{new Date(txn.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Authoritative Audit Trail & Forensics (8 cols) */}
        <div className="lg:col-span-8 flex flex-col bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs h-[700px] overflow-y-auto space-y-5">
          {!selectedTxnId ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20 text-slate-400 font-inter">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center mb-3">
                <FileText className="w-7 h-7 text-slate-400" />
              </div>
              <h3 className="text-base font-bold text-slate-800 font-outfit">No Transaction Selected</h3>
              <p className="text-xs max-w-sm mt-1 text-slate-500">
                Select any transaction from the explorer on the left to inspect its cryptographic SHA-256 lifecycle trace.
              </p>
            </div>
          ) : !auditData ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20 font-inter text-xs text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin text-primary mb-3" />
              <p>Fetching cryptographic audit trace from PostgreSQL...</p>
            </div>
          ) : (
            <>
              {/* Selected Transaction Summary Card */}
              <div
                data-agent-target="forensic-latest-transaction"
                className="bg-slate-50/80 rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-3.5"
              >
                <div className="flex flex-wrap items-start justify-between pb-3 border-b border-slate-200/80 gap-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] text-slate-400 uppercase font-mono font-bold">Transaction ID:</span>
                      <span className="text-xs font-mono font-bold text-slate-900">{auditData.transaction.id}</span>
                      <button
                        onClick={() => handleCopy(auditData.transaction.id, 'txn_id')}
                        className="p-1 text-slate-400 hover:text-primary transition-colors cursor-pointer"
                        title="Copy ID"
                      >
                        {copiedKey === 'txn_id' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <div className="text-xs text-slate-600 font-inter">
                      Product:{' '}
                      <span className="text-slate-900 font-semibold">
                        {auditData.transaction.product_name || auditData.transaction.product_id}
                      </span>
                    </div>
                  </div>

                  <VerdictBadge
                    decision={auditData.transaction.status}
                    status={auditData.transaction.status}
                    reasonCode={auditData.transaction.reason_code}
                    size="md"
                  />
                </div>

                {/* Data Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-inter">
                  <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs">
                    <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Claimed Price</div>
                    <div className="text-sm font-bold text-slate-900 mt-0.5 font-mono">
                      ₹
                      {typeof auditData.transaction.claimed_price === 'number'
                        ? auditData.transaction.claimed_price.toFixed(2)
                        : parseFloat(auditData.transaction.claimed_price || '0').toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs">
                    <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Catalog Total</div>
                    <div className="text-sm font-bold text-emerald-700 mt-0.5 font-mono">
                      ₹
                      {typeof auditData.transaction.authoritative_total === 'number'
                        ? auditData.transaction.authoritative_total.toFixed(2)
                        : parseFloat(auditData.transaction.authoritative_total || '0').toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs">
                    <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Proposed At</div>
                    <div className="text-xs text-slate-800 font-semibold mt-1 font-mono">
                      {new Date(auditData.transaction.created_at).toLocaleTimeString()}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs">
                    <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Executed At</div>
                    <div className="text-xs text-slate-800 font-semibold mt-1 font-mono">
                      {auditData.transaction.executed_at
                        ? new Date(auditData.transaction.executed_at).toLocaleTimeString()
                        : 'Unexecuted'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic SHA-256 Hash Chain Integrity Callout */}
              <div
                className={`rounded-2xl border p-4 transition-all shadow-xs ${
                  auditData.chain_verified
                    ? 'bg-emerald-50/70 border-emerald-200'
                    : 'bg-rose-50/70 border-rose-200'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl ${
                        auditData.chain_verified
                          ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-100 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {auditData.chain_verified ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 font-outfit">
                          Cryptographic Audit Integrity
                        </h4>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border ${
                            auditData.chain_verified
                              ? 'bg-white text-emerald-700 border-emerald-300'
                              : 'bg-white text-rose-700 border-rose-300'
                          }`}
                        >
                          {auditData.chain_verified ? 'SHA-256 Chain Verified' : 'Tamper Detected'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5 font-inter">
                        {auditData.chain_verified
                          ? 'Continuous forward hash-chain verified from genesis event to head. Zero records altered, omitted, or reordered.'
                          : `Hash chain verification error: ${auditData.chain_verification_error}`}
                      </p>
                    </div>
                  </div>

                  <div className="text-right text-xs font-mono text-slate-500">
                    <div>Events: <span className="text-slate-900 font-bold font-mono">{auditData.events.length}</span></div>
                  </div>
                </div>
              </div>

              {/* Reconstructed Deterministic Lifecycle Timeline matching Stitch */}
              <div className="bg-slate-50/60 rounded-2xl border border-slate-200/80 p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-outfit">
                      Reconstructed Lifecycle Timeline
                    </h3>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-primary/10 text-primary rounded-md border border-primary/20">
                      Deterministic
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">Sequence Order (seq_id ASC)</span>
                </div>

                {auditData.events.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-400 font-inter">
                    No audit events recorded for this transaction.
                  </div>
                ) : (
                  <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                    {auditData.events.map((evt) => (
                      <div key={evt.id} className="relative bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs space-y-3">
                        {/* Timeline node pin */}
                        <div className="absolute -left-[19px] top-4 w-3.5 h-3.5 rounded-full bg-white border-2 border-primary ring-2 ring-primary/10"></div>

                        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-slate-900 text-white rounded">
                              SEQ-#{evt.seq_id}
                            </span>
                            <div className="flex items-center gap-1.5 font-outfit text-sm font-bold text-slate-900">
                              {getEventTypeIcon(evt.event_type)}
                              <span>{evt.event_type}</span>
                            </div>
                            <ActorBadge actor={evt.actor} />
                          </div>

                          <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>{new Date(evt.created_at).toLocaleTimeString()}</span>
                          </div>
                        </div>

                        {/* Cryptographic Proof Hashes (SHA-256) */}
                        <div className="bg-[#0B0F19] p-3.5 rounded-xl border border-slate-800 space-y-2 text-xs">
                          <div className="flex items-center justify-between font-inter">
                            <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-xs font-mono">
                              <Lock className="w-3 h-3 text-cyan-400" />
                              <span className="text-[11px] text-slate-300 uppercase tracking-wider">Cryptographic Proof (SHA-256)</span>
                            </div>
                            <button
                              onClick={() => handleCopy(evt.payload_hash, `payload_${evt.id}`)}
                              className="text-slate-400 hover:text-cyan-400 transition-colors flex items-center gap-1 text-[11px] font-mono cursor-pointer"
                            >
                              {copiedKey === `payload_${evt.id}` ? (
                                <>
                                  <Check className="w-3 h-3 text-emerald-400" />
                                  <span className="text-emerald-400 font-bold">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  <span>Copy Hash</span>
                                </>
                              )}
                            </button>
                          </div>

                          <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 text-cyan-300 font-mono text-[11px] break-all shadow-inner tracking-tight">
                            {evt.payload_hash}
                          </div>

                          <div className="flex justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/80 font-mono">
                            <span className="text-slate-400">Prev Chain Link:</span>
                            <span className="text-slate-300 truncate max-w-[280px]" title={evt.prev_hash}>{evt.prev_hash}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
