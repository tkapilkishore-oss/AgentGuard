import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  Bot,
  CreditCard,
  Cpu,
  RefreshCw,
  Copy,
  Check,
  Hash,
  Link2,
  FileText,
  Search,
} from 'lucide-react';
import { api, TransactionSummary, TransactionAuditData } from '../../lib/api';

interface AuditHistoryProps {
  initialTransactionId?: string | null;
  onSelectTransaction?: (transactionId: string) => void;
}

export const AuditHistory: React.FC<AuditHistoryProps> = ({
  initialTransactionId,
}) => {
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(initialTransactionId || null);
  const [auditData, setAuditData] = useState<TransactionAuditData | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [errorList, setErrorList] = useState<string | null>(null);
  const [errorAudit, setErrorAudit] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'SUCCESS' | 'DENIED' | 'ESCALATED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchTransactions = async () => {
    setLoadingList(true);
    setErrorList(null);
    try {
      const res = await api.getTransactions();
      if (res.envelope.success && res.envelope.data) {
        setTransactions(res.envelope.data);
        if (!selectedTxnId && res.envelope.data.length > 0) {
          setSelectedTxnId(res.envelope.data[0].id);
        }
      } else {
        setErrorList(res.envelope.error?.message || 'Failed to load transaction history');
      }
    } catch (err) {
      setErrorList(err instanceof Error ? err.message : 'Network error');
    } finally {
      setLoadingList(false);
    }
  };

  const fetchAuditData = async (txnId: string) => {
    setLoadingAudit(true);
    setErrorAudit(null);
    try {
      const res = await api.getTransactionAudit(txnId);
      if (res.envelope.success && res.envelope.data) {
        setAuditData(res.envelope.data);
      } else {
        setErrorAudit(res.envelope.error?.message || 'Failed to load audit history');
        setAuditData(null);
      }
    } catch (err) {
      setErrorAudit(err instanceof Error ? err.message : 'Network error');
      setAuditData(null);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  useEffect(() => {
    if (selectedTxnId) {
      fetchAuditData(selectedTxnId);
    }
  }, [selectedTxnId]);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(label);
    setTimeout(() => setCopiedId(null), 2000);
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

  const getStatusBadge = (status: string, reasonCode?: string) => {
    const s = status.toUpperCase();
    if (s === 'SUCCESS') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-semibold font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3" />
          <span>SUCCESS</span>
        </span>
      );
    }
    if (s === 'ALLOWED') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-semibold font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3" />
          <span>ALLOWED</span>
        </span>
      );
    }
    if (s === 'ESCALATED') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-semibold font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <AlertTriangle className="w-3 h-3" />
          <span>ESCALATED</span>
        </span>
      );
    }
    if (s === 'DENIED' || s === 'FAILED' || s === 'REVOKED' || s === 'EXPIRED') {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-semibold font-mono bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <XCircle className="w-3 h-3" />
          <span>{reasonCode || s}</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-semibold font-mono bg-slate-800 text-slate-300 border border-slate-700">
        <Clock className="w-3 h-3" />
        <span>{s}</span>
      </span>
    );
  };

  const getActorBadge = (actor: string) => {
    switch (actor.toLowerCase()) {
      case 'agent':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium font-mono bg-purple-500/10 text-purple-300 border border-purple-500/25">
            <Bot className="w-3 h-3" />
            <span>agent (untrusted)</span>
          </span>
        );
      case 'firewall':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium font-mono bg-blue-500/10 text-blue-300 border border-blue-500/25">
            <Cpu className="w-3 h-3" />
            <span>firewall (authoritative)</span>
          </span>
        );
      case 'human':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium font-mono bg-amber-500/10 text-amber-300 border border-amber-500/25">
            <User className="w-3 h-3" />
            <span>human supervisor</span>
          </span>
        );
      case 'razorpay':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium font-mono bg-sky-500/10 text-sky-300 border border-sky-500/25">
            <CreditCard className="w-3 h-3" />
            <span>razorpay test-mode</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-medium font-mono bg-slate-800 text-slate-300 border border-slate-700">
            <User className="w-3 h-3" />
            <span>{actor}</span>
          </span>
        );
    }
  };

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType.toUpperCase()) {
      case 'PROPOSED':
        return <FileText className="w-4 h-4 text-purple-400" />;
      case 'POLICY_DECISION':
        return <Cpu className="w-4 h-4 text-blue-400" />;
      case 'APPROVED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'REJECTED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'EXECUTING':
        return <Clock className="w-4 h-4 text-sky-400" />;
      case 'EXECUTED':
        return <CreditCard className="w-4 h-4 text-emerald-400" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      default:
        return <Hash className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="grid grid-cols-12 gap-6 h-full w-full">
      {/* Left Column: Transaction Explorer (4 cols) */}
      <div className="col-span-4 flex flex-col h-full glass-panel rounded-xl border border-slate-800 p-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">Transaction Explorer</h2>
              <span className="text-xs font-mono px-2 py-0.5 bg-slate-800 text-slate-300 rounded-full border border-slate-700">
                {transactions.length}
              </span>
            </div>
            <p className="text-xs text-slate-400">Authoritative server-side ledger</p>
          </div>
          <button
            onClick={fetchTransactions}
            disabled={loadingList}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors disabled:opacity-50"
            title="Refresh Transactions"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Search & Filter Bar */}
        <div className="pt-3 pb-2 space-y-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, product, reason..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <div className="flex space-x-1 text-xs">
            {(['ALL', 'SUCCESS', 'DENIED', 'ESCALATED'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`flex-1 py-1 rounded text-[11px] font-mono font-medium transition-colors ${
                  filter === f
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Transaction List */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 pt-1">
          {loadingList && transactions.length === 0 && (
            <div className="text-center py-10 text-xs text-slate-500">
              Loading transactions from PostgreSQL...
            </div>
          )}

          {errorList && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300">
              {errorList}
            </div>
          )}

          {!loadingList && filteredTransactions.length === 0 && (
            <div className="text-center py-12 text-xs text-slate-500">
              No transactions recorded yet. Run a proposal via the Shopping Agent or Attack Console.
            </div>
          )}

          {filteredTransactions.map((txn) => {
            const isSelected = txn.id === selectedTxnId;
            const amount = typeof txn.authoritative_total === 'number'
              ? txn.authoritative_total.toFixed(2)
              : parseFloat(txn.authoritative_total || '0').toFixed(2);

            return (
              <div
                key={txn.id}
                onClick={() => setSelectedTxnId(txn.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-slate-800/90 border-indigo-500/60 shadow-md shadow-indigo-950/20'
                    : 'bg-slate-900/60 border-slate-800 hover:bg-slate-850 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-xs font-semibold text-slate-300 tracking-tight">
                    {txn.id.substring(0, 8)}...{txn.id.substring(txn.id.length - 4)}
                  </span>
                  {getStatusBadge(txn.status, txn.reason_code)}
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-200 font-medium truncate max-w-[150px]">
                    {txn.product_name || txn.product_id}
                  </span>
                  <span className="font-mono font-bold text-white">
                    ₹{amount}
                  </span>
                </div>

                <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-800/60 text-[10px] text-slate-400 font-mono">
                  <span>Reason: {txn.reason_code}</span>
                  <span>{new Date(txn.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Column: Authoritative Audit Trail & Forensics (8 cols) */}
      <div className="col-span-8 flex flex-col h-full glass-panel rounded-xl border border-slate-800 p-5 overflow-y-auto space-y-5">
        {!selectedTxnId ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20 text-slate-500">
            <div className="p-4 bg-slate-900 rounded-full mb-3 border border-slate-800 text-slate-600">
              <FileText className="w-8 h-8" />
            </div>
            <h3 className="text-sm font-semibold text-slate-300">No Transaction Selected</h3>
            <p className="text-xs max-w-sm mt-1">
              Select a transaction from the explorer on the left to reconstruct its complete server-generated audit trail.
            </p>
          </div>
        ) : loadingAudit && !auditData ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-20 text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mb-3" />
            <p className="text-xs">Fetching cryptographic audit trace for {selectedTxnId}...</p>
          </div>
        ) : errorAudit ? (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300">
            <div className="flex items-center space-x-2 mb-1 font-semibold">
              <XCircle className="w-4 h-4 text-rose-400" />
              <span>Failed to fetch audit trace</span>
            </div>
            <p>{errorAudit}</p>
          </div>
        ) : auditData ? (
          <>
            {/* Top Bar: Transaction Overview */}
            <div className="bg-slate-900/90 rounded-xl border border-slate-800 p-4">
              <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                <div>
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xs text-slate-400 uppercase font-mono tracking-wider">Transaction ID:</span>
                    <span className="text-xs font-mono font-bold text-white">{auditData.transaction.id}</span>
                    <button
                      onClick={() => handleCopy(auditData.transaction.id, 'txn_id')}
                      className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 transition-colors"
                      title="Copy ID"
                    >
                      {copiedId === 'txn_id' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                  <div className="text-xs text-slate-400">
                    Product: <span className="text-slate-200 font-semibold">{auditData.transaction.product_name || auditData.transaction.product_id}</span> ({auditData.transaction.product_id})
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {getStatusBadge(auditData.transaction.status, auditData.transaction.reason_code)}
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                    {auditData.transaction.reason_code}
                  </span>
                </div>
              </div>

              {/* Data Grid */}
              <div className="grid grid-cols-4 gap-4 pt-3 text-xs">
                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-850">
                  <div className="text-[11px] text-slate-500 font-mono uppercase">Claimed Price</div>
                  <div className="text-sm font-mono font-semibold text-slate-200 mt-0.5">
                    ₹{typeof auditData.transaction.claimed_price === 'number'
                      ? auditData.transaction.claimed_price.toFixed(2)
                      : parseFloat(auditData.transaction.claimed_price || '0').toFixed(2)}
                  </div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-850">
                  <div className="text-[11px] text-slate-500 font-mono uppercase">Authoritative Total</div>
                  <div className="text-sm font-mono font-bold text-emerald-400 mt-0.5">
                    ₹{typeof auditData.transaction.authoritative_total === 'number'
                      ? auditData.transaction.authoritative_total.toFixed(2)
                      : parseFloat(auditData.transaction.authoritative_total || '0').toFixed(2)}
                  </div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-850">
                  <div className="text-[11px] text-slate-500 font-mono uppercase">Proposed At</div>
                  <div className="text-xs font-mono text-slate-300 mt-1">
                    {new Date(auditData.transaction.created_at).toLocaleString()}
                  </div>
                </div>

                <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-850">
                  <div className="text-[11px] text-slate-500 font-mono uppercase">Executed At</div>
                  <div className="text-xs font-mono text-slate-300 mt-1">
                    {auditData.transaction.executed_at
                      ? new Date(auditData.transaction.executed_at).toLocaleString()
                      : 'N/A (Not Executed)'}
                  </div>
                </div>
              </div>
            </div>

            {/* Cryptographic Hash Chain Integrity Status */}
            <div className={`rounded-xl border p-4 transition-all ${
              auditData.chain_verified
                ? 'bg-emerald-950/20 border-emerald-500/30'
                : 'bg-rose-950/20 border-rose-500/30'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className={`p-2 rounded-lg ${
                    auditData.chain_verified
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  }`}>
                    {auditData.chain_verified ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-white">
                        Cryptographic Audit Integrity
                      </h4>
                      <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                        auditData.chain_verified
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                          : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                      }`}>
                        {auditData.chain_verified ? 'SHA-256 CHAIN: VERIFIED' : 'INTEGRITY TAMPER DETECTED'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {auditData.chain_verified
                        ? 'Continuous forward hash-chain verified from genesis through current state head. No records altered, omitted, or reordered.'
                        : `Hash chain verification failed: ${auditData.chain_verification_error}`}
                    </p>
                  </div>
                </div>

                <div className="text-right text-[11px] font-mono text-slate-400">
                  <div>Invariant: <span className="text-slate-300">sha256(prev:event:actor:txn:payload)</span></div>
                  <div>Events Count: <span className="text-indigo-300 font-semibold">{auditData.events.length}</span></div>
                </div>
              </div>
            </div>

            {/* Reconstructed Lifecycle Timeline */}
            <div className="bg-slate-900/70 rounded-xl border border-slate-800 p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Reconstructed Lifecycle Timeline</h3>
                  <span className="text-xs font-mono px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded border border-indigo-500/20">
                    SERVER-GENERATED
                  </span>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  Deterministic Order (seq_id ASC)
                </span>
              </div>

              {auditData.events.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No audit events recorded for this transaction.
                </div>
              ) : (
                <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
                  {auditData.events.map((evt) => {
                    return (
                      <div key={evt.id} className="relative group">
                        {/* Dot on line */}
                        <div className="absolute -left-6 top-1.5 w-6 h-6 rounded-full bg-slate-950 border-2 border-indigo-500 flex items-center justify-center shadow-sm shadow-indigo-500/30">
                          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                        </div>

                        {/* Event Card */}
                        <div className="bg-slate-950/80 rounded-lg border border-slate-800/90 p-3.5 hover:border-slate-700 transition-colors">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700">
                                #{evt.seq_id}
                              </span>
                              <div className="flex items-center space-x-1.5">
                                {getEventTypeIcon(evt.event_type)}
                                <span className="font-mono text-xs font-bold text-white">
                                  {evt.event_type}
                                </span>
                              </div>
                              {getActorBadge(evt.actor)}
                            </div>

                            <div className="flex items-center space-x-1.5 text-xs text-slate-400 font-mono">
                              <Clock className="w-3 h-3 text-slate-500" />
                              <span>{new Date(evt.created_at).toLocaleTimeString()}</span>
                              <span className="text-[10px] text-slate-600">({new Date(evt.created_at).toLocaleDateString()})</span>
                            </div>
                          </div>

                          {/* Cryptographic Link Info */}
                          <div className="mt-2.5 pt-2 border-t border-slate-850 grid grid-cols-2 gap-3 text-[11px] font-mono">
                            <div className="bg-slate-900/80 p-2 rounded border border-slate-800/80">
                              <div className="flex items-center justify-between text-slate-500 mb-0.5">
                                <span className="flex items-center space-x-1">
                                  <Link2 className="w-3 h-3 text-indigo-400" />
                                  <span>Prev Hash</span>
                                </span>
                                <button
                                  onClick={() => handleCopy(evt.prev_hash, `prev_${evt.id}`)}
                                  className="text-slate-500 hover:text-slate-300"
                                  title="Copy Prev Hash"
                                >
                                  {copiedId === `prev_${evt.id}` ? <Check className="w-2.5 h-2.5 text-emerald-400" /> : <Copy className="w-2.5 h-2.5" />}
                                </button>
                              </div>
                              <div className="text-slate-300 truncate font-mono text-[10px]" title={evt.prev_hash}>
                                {evt.prev_hash.substring(0, 16)}...{evt.prev_hash.substring(evt.prev_hash.length - 8)}
                              </div>
                            </div>

                            <div className="bg-slate-900/80 p-2 rounded border border-slate-800/80">
                              <div className="flex items-center justify-between text-slate-500 mb-0.5">
                                <span className="flex items-center space-x-1">
                                  <Hash className="w-3 h-3 text-indigo-400" />
                                  <span>Payload Hash</span>
                                </span>
                                <button
                                  onClick={() => handleCopy(evt.payload_hash, `payload_${evt.id}`)}
                                  className="text-slate-500 hover:text-slate-300"
                                  title="Copy Payload Hash"
                                >
                                  {copiedId === `payload_${evt.id}` ? <Check className="w-2.5 h-2.5 text-emerald-400" /> : <Copy className="w-2.5 h-2.5" />}
                                </button>
                              </div>
                              <div className="text-slate-300 truncate font-mono text-[10px]" title={evt.payload_hash}>
                                {evt.payload_hash.substring(0, 16)}...{evt.payload_hash.substring(evt.payload_hash.length - 8)}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};
