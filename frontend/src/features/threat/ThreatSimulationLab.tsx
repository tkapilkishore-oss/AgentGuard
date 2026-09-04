import React, { useState } from 'react';
import {
  Zap,
  ShieldAlert,
  Repeat,
  AlertOctagon,
  RefreshCw,
  CheckCircle,
  Play,
  RotateCcw,
  Terminal,
  ShieldCheck,
  ShieldX,
  Database,
  ArrowRight,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const ThreatSimulationLab: React.FC = () => {
  const {
    triggerScenario,
    proposeClaim,
    activeTransaction,
    activeAgentClaim,
    rawWireLog,
    loadingAction,
    wireDrawerOpen,
    setWireDrawerOpen,
  } = useAgentGuard();

  const [activeScenarioId, setActiveScenarioId] = useState<number>(3); // Default to price tampering
  const [customPrice, setCustomPrice] = useState<string>('1999');
  const [customQty, setCustomQty] = useState<number>(1);

  // Sync active scenario view with current transaction
  React.useEffect(() => {
    if (
      activeAgentClaim?.product_id === 'prod-002' ||
      Number(activeTransaction?.authoritative_total) === 2799
    ) {
      setActiveScenarioId(1);
    } else if (
      activeAgentClaim?.product_id === 'prod-001' ||
      activeTransaction?.reason_code === 'PRICE_MISMATCH' ||
      Number(activeTransaction?.authoritative_total) === 3499
    ) {
      setActiveScenarioId(3);
    }
  }, [activeTransaction, activeAgentClaim]);

  const handleRunScenario = async (id: number) => {
    setActiveScenarioId(id);
    await triggerScenario(id);
  };

  const handleCustomAttack = async () => {
    const priceNum = parseFloat(customPrice) || 1999;
    await proposeClaim('prod-001', priceNum, customQty);
  };

  const scenarios = [
    {
      id: 1,
      title: 'Happy Path (Baseline)',
      subtitle: 'Standard, un-tampered transaction flow within budget.',
      icon: <CheckCircle className="w-5 h-5 text-verified" />,
      tag: 'ALLOW',
      tagBg: 'bg-[#F0FDF4] text-verified border-[#BBF7D0]',
    },
    {
      id: 2,
      title: 'Over-Budget Escalation',
      subtitle: 'Purchase exceeds mandate limit; escalates to human approver.',
      icon: <AlertOctagon className="w-5 h-5 text-escalation" />,
      tag: 'ESCALATE',
      tagBg: 'bg-[#FEF3C7] text-escalation border-[#FDE68A]',
    },
    {
      id: 3,
      title: 'Price Tampering Attack',
      subtitle: 'Attempting to alter payload prices (₹1,999 vs ₹3,499) in transit.',
      icon: <ShieldAlert className="w-5 h-5 text-denied" />,
      tag: 'DENY',
      tagBg: 'bg-error-container text-error border-error-container',
    },
    {
      id: 4,
      title: 'Replay Attack Defense',
      subtitle: 'Resubmitting a valid transaction to duplicate execution.',
      icon: <Repeat className="w-5 h-5 text-purple-600" />,
      tag: 'DENY (409)',
      tagBg: 'bg-lavender-tint text-[#4C1D95] border-primary-fixed',
    },
    {
      id: 5,
      title: 'Safe Failure & Retry',
      subtitle: 'Gateway decline releases budget; retry succeeds idempotently.',
      icon: <RefreshCw className="w-5 h-5 text-secondary" />,
      tag: 'IDEMPOTENT',
      tagBg: 'bg-secondary-fixed text-[#00346e] border-secondary-container',
    },
    {
      id: 6,
      title: 'Mid-Session Revocation',
      subtitle: 'Mandate revoked mid-flight before payment execution.',
      icon: <RotateCcw className="w-5 h-5 text-denied" />,
      tag: 'DENY (403)',
      tagBg: 'bg-error-container text-error border-error-container',
    },
  ];

  const currentScenario = scenarios.find((s) => s.id === activeScenarioId) || scenarios[2];

  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 max-w-7xl mx-auto w-full space-y-10">
      {/* Title & Introduction */}
      <div className="text-center max-w-3xl mx-auto mb-8">
        <div className="flex items-center justify-center gap-2 mb-3">
          <span className="text-xs font-inter uppercase tracking-wider text-primary font-bold bg-lavender-tint/70 px-3.5 py-1 rounded-full border border-primary-fixed">
            Adversarial Test Suite
          </span>
        </div>
        <h1 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary mb-3">
          Threat Simulation Lab
        </h1>
        <p className="font-inter text-sm sm:text-base text-on-surface-variant leading-relaxed">
          Stress-testing the deterministic boundaries of safe commerce with real-time FastAPI threat simulations.
        </p>
      </div>

      {/* Main Threat Lab Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left Sidebar: Attack Scenario Selector (5 cols) */}
        <aside className="lg:col-span-5 flex flex-col gap-4">
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3.5">
            <div className="flex items-center justify-between">
              <h2 className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-bold flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block"></span>
                Attack Scenarios (6)
              </h2>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">FASTAPI SUITE</span>
            </div>

            <div className="space-y-2">
              {scenarios.map((sc) => {
                const isSelected = activeScenarioId === sc.id;
                const isRunning = loadingAction && activeScenarioId === sc.id;

                return (
                  <button
                    key={sc.id}
                    data-agent-target={
                      sc.id === 3
                        ? 'threat-price-tampering'
                        : sc.id === 1
                        ? 'threat-happy-path'
                        : undefined
                    }
                    onClick={() => handleRunScenario(sc.id)}
                    disabled={loadingAction}
                    className={`w-full text-left rounded-xl p-3.5 transition-all duration-200 flex items-center gap-3 border cursor-pointer ${
                      isSelected
                        ? 'bg-slate-50/90 shadow-xs border-primary ring-1 ring-primary/20'
                        : 'bg-white hover:bg-slate-50/60 hover:border-slate-300 border-slate-200/70'
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${
                      isSelected ? 'bg-white shadow-xs border border-slate-200' : 'bg-slate-100/80'
                    }`}>
                      {sc.icon}
                    </div>

                    <div className="flex-grow min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className={`font-outfit text-sm truncate ${isSelected ? 'font-bold text-primary' : 'font-semibold text-slate-800'}`}>
                          {sc.title}
                        </span>
                        <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-md border tracking-tight ${sc.tagBg}`}>
                          {sc.tag}
                        </span>
                      </div>
                      <p className="font-inter text-xs text-slate-500 line-clamp-2">
                        {sc.subtitle}
                      </p>
                      {sc.id === 1 && (
                        <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                          <span
                            data-agent-target="threat-legitimate-item"
                            className="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#F0FDF4] text-verified rounded-md border border-[#BBF7D0] inline-flex items-center gap-1"
                          >
                            Bluetooth Speaker • ₹2,799
                          </span>
                          <span className="text-[10px] text-slate-400 font-inter">In-budget baseline</span>
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0">
                      <Play className={`w-3.5 h-3.5 transition-transform ${isSelected ? 'text-primary fill-current scale-110' : 'text-slate-300'} ${isRunning ? 'animate-spin' : ''}`} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Attack Parameter Box */}
          <div
            data-agent-target="threat-custom-amount"
            className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs space-y-3 font-inter text-xs"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-primary font-bold font-outfit text-sm">
                <Zap className="w-4 h-4 text-amber-500" />
                <span>Custom Attack Studio</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">INJECTION LAB</span>
            </div>
            <p className="text-slate-500 text-xs">
              Inject custom price claim against Wireless Earbuds (Authoritative catalog price: <strong className="text-verified font-mono font-bold">₹3,499</strong>).
            </p>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-[11px] font-mono uppercase text-slate-500 mb-1 font-semibold">Claimed Price (₹):</label>
                <input
                  type="number"
                  value={customPrice}
                  onChange={(e) => setCustomPrice(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 font-bold font-mono text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-slate-500 mb-1 font-semibold">Quantity (1–10):</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={customQty}
                  onChange={(e) => setCustomQty(parseInt(e.target.value, 10) || 1)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 font-bold font-mono text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
                />
              </div>
            </div>

            <button
              onClick={handleCustomAttack}
              disabled={loadingAction}
              className="w-full py-2.5 bg-primary hover:bg-slate-800 text-white font-inter text-xs font-semibold rounded-xl transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer active:scale-98"
            >
              <Zap className="w-3.5 h-3.5 fill-current text-amber-400" />
              <span>Inject Custom Claim to Firewall</span>
            </button>
          </div>
        </aside>

        {/* Center/Right: Simulation Canvas (7 cols) */}
        <section className="lg:col-span-7 bg-white rounded-2xl p-6 sm:p-7 border border-slate-200/80 flex flex-col justify-between shadow-xs relative overflow-hidden">
          {/* Subtle background decorative grid */}
          <div className="absolute inset-0 bg-radial-[circle_at_top_right] from-primary/3 via-transparent to-transparent pointer-events-none" />

          {/* Simulation Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-200/80 relative z-10">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">Active Simulation Environment</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              </div>
              <h3 className="font-outfit text-lg sm:text-xl font-bold text-slate-900 mt-0.5">{currentScenario.title}</h3>
            </div>
            <span className={`px-3 py-1 text-xs font-mono font-bold rounded-lg border shadow-xs ${currentScenario.tagBg}`}>
              {activeTransaction?.reason_code || currentScenario.tag}
            </span>
          </div>

          {/* Interactive Flow Visualizer */}
          <div className="py-8 sm:py-12 relative z-10 flex flex-col items-center justify-center gap-7">
            <div className="flex items-center justify-between w-full max-w-2xl relative px-3 sm:px-6">
              {/* Center Line with subtle glow */}
              <div className="absolute top-1/2 left-8 right-8 h-1 bg-gradient-to-r from-slate-200 via-primary/35 to-slate-200 -translate-y-1/2 z-0 rounded-full"></div>

              {/* Node 1: Origin Terminal */}
              <div className="flex flex-col items-center gap-2.5 z-10">
                <div className="w-18 h-18 sm:w-22 sm:h-22 rounded-2xl bg-white shadow-xs flex items-center justify-center border-2 border-slate-200/90 transition-all hover:border-slate-300">
                  <Terminal className="w-9 h-9 sm:w-11 sm:h-11 text-slate-700" />
                </div>
                <div className="text-center">
                  <span className="text-xs sm:text-sm font-mono uppercase tracking-wider text-slate-700 font-bold block">Untrusted LLM</span>
                  <span className="text-[10px] font-mono text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-200/70 inline-block mt-0.5 font-semibold">Agent Claim</span>
                </div>
              </div>

              {/* Node 2: AgentGuard Analyzing Core (The Central Visual Focal Point) */}
              <div className="relative w-40 h-40 sm:w-48 sm:h-48 flex items-center justify-center z-10">
                <div className="absolute inset-0 bg-primary/15 rounded-full blur-2xl animate-pulse"></div>
                <div className="w-28 h-28 sm:w-36 sm:h-36 rounded-full bg-primary flex items-center justify-center text-white ring-8 ring-primary/15 shadow-xl transition-all duration-300 border-2 border-white/20">
                  {activeTransaction?.decision === 'ALLOW' ? (
                    <ShieldCheck className="w-14 h-14 sm:w-18 sm:h-18 text-emerald-400 drop-shadow-md" />
                  ) : activeTransaction?.decision === 'ESCALATE' ? (
                    <AlertOctagon className="w-14 h-14 sm:w-18 sm:h-18 text-amber-400 drop-shadow-md" />
                  ) : (
                    <ShieldX className="w-14 h-14 sm:w-18 sm:h-18 text-rose-400 drop-shadow-md" />
                  )}
                </div>
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] sm:text-[11px] font-mono font-bold uppercase tracking-widest px-3.5 py-1 rounded-full shadow-md border border-slate-700 whitespace-nowrap">
                  {loadingAction ? 'Analyzing Invariants' : 'Deterministic Core'}
                </div>
                <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                  <span className="text-[10px] sm:text-[11px] font-outfit uppercase tracking-wider text-primary font-extrabold bg-white/95 px-3 py-0.5 rounded-full border border-primary/20 shadow-xs">
                    Firewall Cross-Verification
                  </span>
                </div>
              </div>

              {/* Node 3: Authoritative Ledger */}
              <div className="flex flex-col items-center gap-2.5 z-10">
                <div className="w-18 h-18 sm:w-22 sm:h-22 rounded-2xl bg-white shadow-xs flex items-center justify-center border-2 border-slate-200/90 transition-all hover:border-slate-300">
                  <Database className="w-9 h-9 sm:w-11 sm:h-11 text-secondary" />
                </div>
                <div className="text-center">
                  <span className="text-xs sm:text-sm font-mono uppercase tracking-wider text-secondary font-bold block">PostgreSQL</span>
                  <span className="text-[10px] font-mono text-secondary bg-secondary-fixed/50 px-2 py-0.5 rounded border border-secondary-container inline-block mt-0.5 font-semibold">Authoritative Catalog</span>
                </div>
              </div>
            </div>

            {/* Verdict Callout Banner */}
            <div
              data-agent-target="decision-result"
              className="bg-slate-50/90 px-6 py-3.5 rounded-xl border border-slate-200/90 shadow-xs flex flex-col items-center gap-1.5 max-w-md w-full text-center"
            >
              <div className="flex items-center gap-2">
                {activeTransaction?.decision === 'ALLOW' ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    <span className="text-emerald-700 font-outfit text-sm font-bold">Authorization Approved</span>
                  </>
                ) : activeTransaction?.decision === 'ESCALATE' ? (
                  <>
                    <AlertOctagon className="w-4 h-4 text-amber-600" />
                    <span className="text-amber-700 font-outfit text-sm font-bold">Escalated to Human Approver</span>
                  </>
                ) : (
                  <>
                    <ShieldX className="w-4 h-4 text-rose-600" />
                    <span className="text-rose-700 font-outfit text-sm font-bold">Threat Neutralized</span>
                  </>
                )}
              </div>

              <div className="h-px w-full bg-slate-200 my-0.5"></div>

              <p className="text-xs text-slate-600 font-inter">
                Reason Code: <span className="font-mono font-bold text-slate-900">{activeTransaction?.reason_code || 'PRICE_MISMATCH'}</span>
              </p>
            </div>
          </div>

          {/* System Kernel / Telemetry Log View - Dark Command Console */}
          <div className="relative z-10 w-full bg-[#0B0F19] rounded-xl p-4 text-xs text-slate-200 shadow-inner border border-slate-800/90 overflow-x-auto">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></div>
                </div>
                <span className="text-slate-300 text-[11px] font-mono font-bold uppercase tracking-wider ml-1.5 flex items-center gap-1.5">
                  <Terminal className="w-3 h-3 text-cyan-400" />
                  System Kernel Output
                </span>
              </div>
              <button
                onClick={() => setWireDrawerOpen(!wireDrawerOpen)}
                className="text-slate-400 hover:text-cyan-400 transition-colors flex items-center gap-1 text-[11px] font-mono cursor-pointer"
              >
                <span>Inspect Wire</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-1.5 text-xs font-mono leading-relaxed">
              <div className="flex gap-3 text-slate-400">
                <span className="text-slate-600 shrink-0">{rawWireLog ? rawWireLog.timestamp : '14:02:11'}</span>
                <span className="text-cyan-400 font-bold shrink-0">[INFO]</span>
                <span className="truncate">Ingesting untrusted candidate payload for deterministic evaluation</span>
              </div>
              <div className="flex gap-3 text-slate-400">
                <span className="text-slate-600 shrink-0">{rawWireLog ? rawWireLog.timestamp : '14:02:11'}</span>
                <span className="text-amber-400 font-bold shrink-0">[EVAL]</span>
                <span className="truncate">Executing pure policy engine against PostgreSQL catalog truth...</span>
              </div>
              <div className={`flex gap-3 px-3 py-1 rounded-md ${
                activeTransaction?.decision === 'ALLOW'
                  ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 font-semibold'
                  : activeTransaction?.decision === 'ESCALATE'
                  ? 'bg-amber-950/40 text-amber-300 border border-amber-800/40 font-semibold'
                  : 'bg-rose-950/40 text-rose-300 border border-rose-800/40 font-semibold'
              }`}>
                <span className="shrink-0 text-slate-500">{rawWireLog ? rawWireLog.timestamp : '14:02:12'}</span>
                <span className="font-bold shrink-0">[{activeTransaction?.decision || 'DENY'}]</span>
                <span className="truncate">
                  {activeTransaction?.decision === 'ALLOW'
                    ? 'Policy evaluation passed: Transaction authorized for execution'
                    : activeTransaction?.decision === 'ESCALATE'
                    ? 'Threshold violation: Human supervisor approval required'
                    : `Security violation: ${activeTransaction?.reason_code || 'PRICE_MISMATCH'} detected.`}
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
