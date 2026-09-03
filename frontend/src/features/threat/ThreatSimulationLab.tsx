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
    rawWireLog,
    loadingAction,
    wireDrawerOpen,
    setWireDrawerOpen,
  } = useAgentGuard();

  const [activeScenarioId, setActiveScenarioId] = useState<number>(3); // Default to price tampering
  const [customPrice, setCustomPrice] = useState<string>('1999');
  const [customQty, setCustomQty] = useState<number>(1);

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
          <div className="bg-white rounded-2xl p-5 border border-surface-container shadow-ambient-1 space-y-3">
            <h2 className="text-xs font-inter uppercase tracking-wider text-outline font-bold">
              Attack Scenarios
            </h2>

            <div className="space-y-2.5">
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
                    className={`w-full text-left rounded-xl p-4 transition-all duration-300 flex items-center gap-3.5 border ${
                      isSelected
                        ? 'bg-white shadow-ambient-2 border-l-4 border-primary ring-1 ring-primary/10'
                        : 'bg-white/60 hover:bg-white hover:shadow-ambient-1 border-surface-container'
                    }`}
                  >
                    <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center flex-shrink-0">
                      {sc.icon}
                    </div>

                    <div className="flex-grow min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className={`font-outfit text-sm truncate ${isSelected ? 'font-bold text-primary' : 'font-semibold text-on-surface'}`}>
                          {sc.title}
                        </span>
                        <span className={`px-2 py-0.5 text-xs font-inter font-semibold rounded-full border ${sc.tagBg}`}>
                          {sc.tag}
                        </span>
                      </div>
                      <p className="font-inter text-xs text-on-surface-variant line-clamp-2">
                        {sc.subtitle}
                      </p>
                    </div>

                    <div className="flex-shrink-0">
                      <Play className={`w-3.5 h-3.5 ${isSelected ? 'text-primary fill-current' : 'text-outline'} ${isRunning ? 'animate-spin' : ''}`} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Attack Parameter Box */}
          <div className="bg-white rounded-2xl p-5 border border-surface-container shadow-ambient-1 space-y-3 font-inter text-xs">
            <div className="flex items-center gap-2 text-primary font-bold font-outfit text-sm">
              <Zap className="w-4 h-4 text-escalation" />
              <span>Custom Attack Studio</span>
            </div>
            <p className="text-on-surface-variant text-xs">
              Inject custom price claim against Wireless Earbuds (Database price: <strong className="text-verified font-mono">₹3,499</strong>).
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-on-surface-variant mb-1 font-semibold">Claimed Price (₹):</label>
                <input
                  type="number"
                  value={customPrice}
                  onChange={(e) => setCustomPrice(e.target.value)}
                  className="w-full bg-surface-container-low border border-surface-container rounded-xl px-3 py-2 text-primary font-bold font-mono text-xs focus:outline-none focus:border-secondary"
                />
              </div>

              <div>
                <label className="block text-xs text-on-surface-variant mb-1 font-semibold">Quantity (1–10):</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={customQty}
                  onChange={(e) => setCustomQty(parseInt(e.target.value, 10) || 1)}
                  className="w-full bg-surface-container-low border border-surface-container rounded-xl px-3 py-2 text-primary font-bold font-mono text-xs focus:outline-none focus:border-secondary"
                />
              </div>
            </div>

            <button
              onClick={handleCustomAttack}
              disabled={loadingAction}
              className="w-full py-2.5 bg-primary hover:bg-secondary text-white font-inter text-xs font-bold rounded-full transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5 fill-current" />
              <span>Inject Custom Claim to Firewall</span>
            </button>
          </div>
        </aside>

        {/* Center/Right: Simulation Canvas (7 cols) */}
        <section className="lg:col-span-7 bg-white rounded-2xl p-6 sm:p-8 border border-surface-container flex flex-col justify-between shadow-ambient-1 relative overflow-hidden">
          {/* Simulation Header */}
          <div className="flex items-center justify-between pb-4 border-b border-surface-container relative z-10">
            <div>
              <span className="text-xs font-inter uppercase tracking-wider text-outline font-semibold">Active Simulation</span>
              <h3 className="font-outfit text-lg sm:text-xl font-bold text-primary">{currentScenario.title}</h3>
            </div>
            <span className={`px-3 py-1 text-xs font-inter font-bold rounded-full border ${currentScenario.tagBg}`}>
              {activeTransaction?.reason_code || currentScenario.tag}
            </span>
          </div>

          {/* Interactive Flow Visualizer */}
          <div className="py-8 relative z-10 flex flex-col items-center justify-center gap-6">
            <div className="flex items-center justify-between w-full max-w-lg relative">
              {/* Center Line */}
              <div className="absolute top-1/2 left-0 w-full h-0.5 bg-surface-container-high -translate-y-1/2 z-0"></div>

              {/* Node 1: Origin Terminal */}
              <div className="flex flex-col items-center gap-2 z-10">
                <div className="w-14 h-14 rounded-2xl bg-white shadow-ambient-1 flex items-center justify-center border border-surface-container">
                  <Terminal className="w-6 h-6 text-on-surface-variant" />
                </div>
                <span className="text-xs font-inter uppercase tracking-wider text-on-surface-variant font-semibold">Untrusted LLM</span>
              </div>

              {/* Node 2: AgentGuard Analyzing Core */}
              <div className="relative w-36 h-36 flex items-center justify-center z-10">
                <div className="absolute inset-0 bg-lavender-tint opacity-40 rounded-full blur-2xl animate-pulse"></div>
                <div className="w-24 h-24 rounded-full bg-primary flex items-center justify-center text-white ring-8 ring-lavender-tint shadow-lg">
                  {activeTransaction?.decision === 'ALLOW' ? (
                    <ShieldCheck className="w-10 h-10 text-verified" />
                  ) : activeTransaction?.decision === 'ESCALATE' ? (
                    <AlertOctagon className="w-10 h-10 text-escalation" />
                  ) : (
                    <ShieldX className="w-10 h-10 text-denied" />
                  )}
                </div>
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-white text-[10px] font-inter font-bold px-2.5 py-0.5 rounded-full shadow-md">
                  {loadingAction ? 'Analyzing' : 'Verified'}
                </div>
              </div>

              {/* Node 3: Authoritative Ledger */}
              <div className="flex flex-col items-center gap-2 z-10">
                <div className="w-14 h-14 rounded-2xl bg-white shadow-ambient-1 flex items-center justify-center border border-surface-container">
                  <Database className="w-6 h-6 text-secondary" />
                </div>
                <span className="text-xs font-inter uppercase tracking-wider text-secondary font-semibold">PostgreSQL</span>
              </div>
            </div>

            {/* Verdict Callout Banner */}
            <div
              data-agent-target="decision-result"
              className="glass-panel px-6 py-4 rounded-2xl border border-surface-container shadow-ambient-2 flex flex-col items-center gap-2 max-w-md w-full text-center"
            >
              <div className="flex items-center gap-2">
                {activeTransaction?.decision === 'ALLOW' ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-verified" />
                    <span className="text-verified font-outfit text-base font-bold">Authorization Approved</span>
                  </>
                ) : activeTransaction?.decision === 'ESCALATE' ? (
                  <>
                    <AlertOctagon className="w-5 h-5 text-escalation" />
                    <span className="text-escalation font-outfit text-base font-bold">Escalated to Human</span>
                  </>
                ) : (
                  <>
                    <ShieldX className="w-5 h-5 text-denied" />
                    <span className="text-denied font-outfit text-base font-bold">Threat Neutralized</span>
                  </>
                )}
              </div>

              <div className="h-px w-full bg-surface-container my-1"></div>

              <p className="text-xs text-on-surface font-inter">
                Reason Code: <span className="font-mono font-bold">{activeTransaction?.reason_code || 'PRICE_MISMATCH'}</span>
              </p>
            </div>
          </div>

          {/* System Kernel / Telemetry Log View matching Stitch */}
          <div className="relative z-10 w-full bg-surface-container-low rounded-xl p-4 text-xs text-on-surface shadow-sm border border-surface-container overflow-x-auto">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-surface-container">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-error"></div>
                  <div className="w-2 h-2 rounded-full bg-escalation"></div>
                  <div className="w-2 h-2 rounded-full bg-verified"></div>
                </div>
                <span className="text-primary text-xs font-inter font-bold uppercase tracking-wider ml-1">
                  System Kernel Output
                </span>
              </div>
              <button
                onClick={() => setWireDrawerOpen(!wireDrawerOpen)}
                className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 text-xs font-inter font-medium"
              >
                <span>Inspect Wire</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-1.5 text-xs font-mono leading-relaxed">
              <div className="flex gap-3 text-on-surface-variant">
                <span className="text-outline shrink-0">{rawWireLog ? rawWireLog.timestamp : '14:02:11'}</span>
                <span className="text-secondary font-bold font-inter">[INFO]</span>
                <span className="font-inter">Ingesting untrusted candidate payload for evaluation</span>
              </div>
              <div className="flex gap-3 text-on-surface-variant">
                <span className="text-outline shrink-0">{rawWireLog ? rawWireLog.timestamp : '14:02:11'}</span>
                <span className="text-escalation font-bold font-inter">[EVAL]</span>
                <span className="font-inter">Executing pure policy engine against PostgreSQL catalog truth...</span>
              </div>
              <div className={`flex gap-3 px-3 py-1 rounded-lg ${activeTransaction?.decision === 'ALLOW' ? 'bg-[#F0FDF4] text-verified font-semibold' : activeTransaction?.decision === 'ESCALATE' ? 'bg-[#FEF3C7] text-escalation font-semibold' : 'bg-error-container/40 text-denied font-bold'}`}>
                <span className="shrink-0">{rawWireLog ? rawWireLog.timestamp : '14:02:12'}</span>
                <span className="font-bold font-inter">[{activeTransaction?.decision || 'DENY'}]</span>
                <span className="font-inter">
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
