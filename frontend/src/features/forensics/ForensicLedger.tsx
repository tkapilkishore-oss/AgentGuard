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
        <div className="lg:col-span-4 flex flex-col bg-white rounded-2xl border border-surface-container p-5 shadow-ambient-1 h-[680px]">
          {/* Explorer Header */}
          <div className="flex items-center justify-between pb-3 border-b border-surface-container">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-bold text-primary uppercase tracking-wider font-inter">
                  Transaction Explorer
                </h2>
                <span className="text-xs font-inter font-bold px-2 py-0.5 bg-surface-container text-primary rounded-full border border-surface-container">
                  {transactions.length}
                </span>
              </div>
              <p className="text-xs text-on-surface-variant font-inter mt-0.5">Authoritative PostgreSQL Records</p>
            </div>
            <button
              onClick={fetchTransactions}
              disabled={loadingAction}
              className="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded-full transition-colors"
              title="Refresh Transactions"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingAction ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Search & Filter Bar */}
          <div className="pt-3 pb-2 space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-on-surface-variant absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID, product, reason..."
                className="w-full bg-surface-container-low border border-surface-container rounded-full pl-9 pr-4 py-2 text-xs text-primary placeholder:text-outline focus:outline-none focus:border-secondary font-inter"
              />
            </div>

            <div className="flex gap-1 font-inter">
              {(['ALL', 'SUCCESS', 'DENIED', 'ESCALATED'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`flex-1 py-1 rounded-full text-xs font-semibold transition-all ${
                    filter === f
                      ? 'bg-primary text-white shadow-sm'
                      : 'bg-surface-container-low text-on-surface-variant hover:text-primary border border-surface-container'
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
              <div className="text-center py-12 text-xs text-on-surface-variant font-inter">
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
                      ? 'bg-white border-primary shadow-ambient-2 ring-1 ring-primary/10'
                      : 'bg-surface-container-low/60 border-surface-container hover:bg-white hover:border-surface-container-high'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-primary">
                      {txn.id.substring(0, 8)}...{txn.id.substring(txn.id.length - 4)}
                    </span>
                    <VerdictBadge decision={txn.status} status={txn.status} reasonCode={txn.reason_code} size="sm" />
                  </div>

                  <div className="flex items-center justify-between text-xs font-inter">
                    <span className="text-on-surface font-medium truncate max-w-[140px]">
                      {txn.product_name || txn.product_id}
                    </span>
                    <span className="font-mono font-bold text-primary">₹{amount}</span>
                  </div>

                  <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-surface-container text-[11px] text-on-surface-variant font-inter">
                    <span className="font-mono">{txn.reason_code}</span>
                    <span className="font-mono">{new Date(txn.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Authoritative Audit Trail & Forensics (8 cols) */}
        <div className="lg:col-span-8 flex flex-col bg-white rounded-2xl border border-surface-container p-6 shadow-ambient-1 h-[680px] overflow-y-auto space-y-5">
          {!selectedTxnId ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20 text-on-surface-variant font-inter">
              <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center mb-3">
                <FileText className="w-8 h-8 text-outline" />
              </div>
              <h3 className="text-base font-bold text-primary font-outfit">No Transaction Selected</h3>
              <p className="text-xs max-w-sm mt-1">
                Select any transaction from the explorer on the left to inspect its cryptographic SHA-256 lifecycle trace.
              </p>
            </div>
          ) : !auditData ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20 font-inter text-xs text-on-surface-variant">
              <RefreshCw className="w-6 h-6 animate-spin text-secondary mb-3" />
              <p>Fetching cryptographic audit trace from PostgreSQL...</p>
            </div>
          ) : (
            <>
              {/* Selected Transaction Summary Card */}
              <div
                data-agent-target="forensic-latest-transaction"
                className="bg-surface rounded-2xl border border-surface-container p-5 shadow-sm space-y-3"
              >
                <div className="flex flex-wrap items-start justify-between pb-3 border-b border-surface-container gap-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-on-surface-variant uppercase font-inter font-bold">Transaction ID:</span>
                      <span className="text-xs font-mono font-bold text-primary">{auditData.transaction.id}</span>
                      <button
                        onClick={() => handleCopy(auditData.transaction.id, 'txn_id')}
                        className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                        title="Copy ID"
                      >
                        {copiedKey === 'txn_id' ? <Check className="w-3 h-3 text-verified" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <div className="text-xs text-on-surface-variant font-inter">
                      Product:{' '}
                      <span className="text-primary font-bold">
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
                  <div className="bg-white p-3 rounded-xl border border-surface-container">
                    <div className="text-[10px] text-on-surface-variant font-semibold uppercase">Claimed Price</div>
                    <div className="text-sm font-bold text-primary mt-0.5 font-mono">
                      ₹
                      {typeof auditData.transaction.claimed_price === 'number'
                        ? auditData.transaction.claimed_price.toFixed(2)
                        : parseFloat(auditData.transaction.claimed_price || '0').toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-surface-container">
                    <div className="text-[10px] text-on-surface-variant font-semibold uppercase">Catalog Total</div>
                    <div className="text-sm font-bold text-verified mt-0.5 font-mono">
                      ₹
                      {typeof auditData.transaction.authoritative_total === 'number'
                        ? auditData.transaction.authoritative_total.toFixed(2)
                        : parseFloat(auditData.transaction.authoritative_total || '0').toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-surface-container">
                    <div className="text-[10px] text-on-surface-variant font-semibold uppercase">Proposed At</div>
                    <div className="text-xs text-primary font-semibold mt-1 font-mono">
                      {new Date(auditData.transaction.created_at).toLocaleTimeString()}
                    </div>
                  </div>

                  <div className="bg-white p-3 rounded-xl border border-surface-container">
                    <div className="text-[10px] text-on-surface-variant font-semibold uppercase">Executed At</div>
                    <div className="text-xs text-primary font-semibold mt-1 font-mono">
                      {auditData.transaction.executed_at
                        ? new Date(auditData.transaction.executed_at).toLocaleTimeString()
                        : 'Unexecuted'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic SHA-256 Hash Chain Integrity Callout */}
              <div
                className={`rounded-2xl border p-4 transition-all shadow-sm ${
                  auditData.chain_verified
                    ? 'bg-[#F0FDF4] border-[#BBF7D0]'
                    : 'bg-error-container/30 border-error-container'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl ${
                        auditData.chain_verified
                          ? 'bg-emerald-100 text-verified'
                          : 'bg-error-container text-error'
                      }`}
                    >
                      {auditData.chain_verified ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-primary font-outfit">
                          Cryptographic Audit Integrity
                        </h4>
                        <span
                          className={`text-xs font-inter font-semibold px-2.5 py-0.5 rounded-full border ${
                            auditData.chain_verified
                              ? 'bg-white text-verified border-[#BBF7D0]'
                              : 'bg-white text-error border-error-container'
                          }`}
                        >
                          {auditData.chain_verified ? 'SHA-256 Chain Verified' : 'Tamper Detected'}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant mt-0.5 font-inter">
                        {auditData.chain_verified
                          ? 'Continuous forward hash-chain verified from genesis event to head. Zero records altered, omitted, or reordered.'
                          : `Hash chain verification error: ${auditData.chain_verification_error}`}
                      </p>
                    </div>
                  </div>

                  <div className="text-right text-xs font-inter text-on-surface-variant">
                    <div>Events Count: <span className="text-primary font-bold font-mono">{auditData.events.length}</span></div>
                  </div>
                </div>
              </div>

              {/* Reconstructed Deterministic Lifecycle Timeline matching Stitch */}
              <div className="bg-surface rounded-2xl border border-surface-container p-5 space-y-4 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-surface-container">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-primary uppercase tracking-wider font-inter">
                      Reconstructed Lifecycle Timeline
                    </h3>
                    <span className="text-xs font-inter font-semibold px-2.5 py-0.5 bg-lavender-tint text-[#4C1D95] rounded-full border border-primary-fixed">
                      Deterministic
                    </span>
                  </div>
                  <span className="text-xs text-on-surface-variant font-inter">Sequence Order (seq_id ASC)</span>
                </div>

                {auditData.events.length === 0 ? (
                  <div className="py-8 text-center text-xs text-on-surface-variant font-inter">
                    No audit events recorded for this transaction.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {auditData.events.map((evt) => (
                      <div key={evt.id} className="bg-white rounded-2xl p-5 border border-surface-container shadow-sm space-y-3">
                        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-surface-container">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold px-2.5 py-0.5 bg-primary text-white rounded shadow-sm">
                              SEQ-#{evt.seq_id}
                            </span>
                            <div className="flex items-center gap-1.5 font-outfit text-sm font-bold text-primary">
                              {getEventTypeIcon(evt.event_type)}
                              <span>{evt.event_type}</span>
                            </div>
                            <ActorBadge actor={evt.actor} />
                          </div>

                          <div className="flex items-center gap-1 text-xs text-on-surface-variant font-mono">
                            <Clock className="w-3.5 h-3.5 text-outline" />
                            <span>{new Date(evt.created_at).toLocaleTimeString()}</span>
                          </div>
                        </div>

                        {/* Cryptographic Proof Hashes (SHA-256) matching Stitch */}
                        <div className="bg-surface-container-low p-3.5 rounded-xl border border-surface-container space-y-2 text-xs">
                          <div className="flex items-center justify-between font-inter">
                            <div className="flex items-center gap-1.5 text-on-surface-variant font-semibold text-xs">
                              <Lock className="w-3.5 h-3.5 text-outline" />
                              <span>Cryptographic Proof (SHA-256)</span>
                            </div>
                            <button
                              onClick={() => handleCopy(evt.payload_hash, `payload_${evt.id}`)}
                              className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 text-xs font-inter"
                            >
                              {copiedKey === `payload_${evt.id}` ? (
                                <>
                                  <Check className="w-3 h-3 text-verified" />
                                  <span className="text-verified font-bold">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  <span>Copy Hash</span>
                                </>
                              )}
                            </button>
                          </div>

                          <div className="bg-white p-2.5 rounded-lg border border-surface-container text-primary font-bold font-mono text-[11px] break-all shadow-inner">
                            {evt.payload_hash}
                          </div>

                          <div className="flex justify-between text-[11px] text-on-surface-variant pt-1 border-t border-surface-container font-inter">
                            <span>Prev Chain Link:</span>
                            <span className="font-mono truncate max-w-[280px]" title={evt.prev_hash}>{evt.prev_hash}</span>
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
