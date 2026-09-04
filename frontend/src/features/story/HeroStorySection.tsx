import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  Bot,
  CreditCard,
  Play,
  Mic,
  ArrowRight,
} from 'lucide-react';
import { gsap } from 'gsap';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const HeroStorySection: React.FC = () => {
  const navigate = useNavigate();
  const {
    triggerScenario,
    setIsConversationalOpen,
    loadingAction,
  } = useAgentGuard();

  const heroRef = useRef<HTMLDivElement>(null);
  const headlineRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const metricsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

      tl.fromTo(
        headlineRef.current,
        { y: 28, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8 }
      )
        .fromTo(
          subtitleRef.current,
          { y: 18, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.6 },
          '-=0.4'
        )
        .fromTo(
          ctaRef.current,
          { y: 18, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5 },
          '-=0.3'
        )
        .fromTo(
          metricsRef.current?.children ? Array.from(metricsRef.current.children) : [],
          { y: 20, opacity: 0, scale: 0.97 },
          { y: 0, opacity: 1, scale: 1, duration: 0.5, stagger: 0.1 },
          '-=0.2'
        );
    }, heroRef);

    return () => ctx.revert();
  }, []);

  const handleRunLiveDemo = async () => {
    navigate('/live');
    await triggerScenario(3); // Real price tampering verification flow
  };

  const handleTalkToAgent = () => {
    setIsConversationalOpen(true);
  };

  return (
    <section
      ref={heroRef}
      id="hero"
      className="relative pt-12 pb-16 px-4 sm:px-6 max-w-7xl mx-auto w-full flex flex-col items-center justify-center text-center overflow-hidden"
    >
      {/* Ambient Radial Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[450px] bg-surface-glow pointer-events-none rounded-full blur-3xl -z-10 opacity-70" />

      {/* Authority Pill Badge */}
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-lavender-tint/90 border border-primary-fixed text-[#4C1D95] text-xs font-inter font-semibold mb-6 shadow-sm">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-verified opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-verified"></span>
        </span>
        <span>Agentic Commerce Firewall & Trust Boundary</span>
      </div>

      {/* Editorial Headline */}
      <h1
        ref={headlineRef}
        className="font-outfit text-4xl sm:text-6xl lg:text-7xl font-extrabold text-primary tracking-tight leading-[1.08] max-w-5xl mb-6"
      >
        Give AI agents a <br className="hidden sm:inline" />
        <span className="bg-gradient-to-r from-primary via-primary-container to-secondary bg-clip-text text-transparent">
          secure path to commerce.
        </span>
      </h1>

      {/* Subtitle */}
      <p
        ref={subtitleRef}
        className="font-inter text-base sm:text-xl text-on-surface-variant max-w-3xl leading-relaxed mb-8"
      >
        Autonomous agent transactions before money moves. AgentGuard serves as the definitive server-authoritative trust boundary between intelligent AI agents and your foundational financial ledgers.
      </p>

      {/* Primary CTAs */}
      <div ref={ctaRef} className="flex flex-wrap items-center justify-center gap-3.5 sm:gap-5 mb-14">
        <button
          onClick={handleRunLiveDemo}
          disabled={loadingAction}
          className="px-7 sm:px-9 py-3.5 bg-primary hover:bg-secondary text-white rounded-full font-inter font-semibold text-sm sm:text-base ambient-shadow-2 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5 disabled:opacity-50 group"
        >
          <Play className="w-4 h-4 fill-current text-white group-hover:scale-110 transition-transform" />
          <span>Launch Live Protection</span>
        </button>

        <button
          onClick={handleTalkToAgent}
          className="px-7 sm:px-9 py-3.5 bg-white hover:bg-lavender-tint/60 text-primary border border-surface-container-high rounded-full font-inter font-semibold text-sm sm:text-base ambient-shadow-1 hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5"
        >
          <Mic className="w-4 h-4 text-secondary" />
          <span>Talk to AgentGuard</span>
        </button>

        <button
          onClick={() => navigate('/threats')}
          className="px-5 py-3.5 text-on-surface-variant hover:text-primary rounded-full font-inter font-medium text-xs sm:text-sm flex items-center gap-1.5 transition-colors"
        >
          <span>Threat Simulation Lab</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 3 Core Architecture Metric Cards */}
      <div
        ref={metricsRef}
        className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 w-full max-w-5xl text-left"
      >
        {/* Card 1 */}
        <div className="bg-white/95 rounded-2xl p-5 sm:p-6 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-error-container/40 text-error flex items-center justify-center border border-error-container/60">
              <Bot className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-inter font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-error-container/30 text-error border border-error-container/40">
              Zero Trust
            </span>
          </div>
          <div>
            <div className="text-[10px] font-inter font-semibold uppercase tracking-wider text-on-surface-variant/70 mb-0.5">
              Invariant Layer 01
            </div>
            <h3 className="font-outfit font-bold text-primary text-base sm:text-lg mb-1">
              Zero Prompt Authority
            </h3>
            <p className="font-inter text-xs text-on-surface-variant leading-relaxed">
              Prompt injections cannot alter prices or budget thresholds. The LLM is strictly an untrusted proposer.
            </p>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-white/95 rounded-2xl p-5 sm:p-6 border border-primary/30 shadow-[0_2px_5px_rgba(15,23,42,0.04),0_12px_28px_rgba(59,7,100,0.08)] card-depth-hover flex flex-col justify-between space-y-3 ring-1 ring-primary/10">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-primary text-white flex items-center justify-center shadow-sm ring-4 ring-lavender-tint/80">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-[10px] font-inter font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-lavender-tint text-[#4C1D95] border border-primary-fixed">
              Deterministic
            </span>
          </div>
          <div>
            <div className="text-[10px] font-inter font-semibold uppercase tracking-wider text-on-surface-variant/70 mb-0.5">
              Invariant Layer 02
            </div>
            <h3 className="font-outfit font-bold text-primary text-base sm:text-lg mb-1">
              PostgreSQL Truth Gate
            </h3>
            <p className="font-inter text-xs text-on-surface-variant leading-relaxed">
              Authoritative catalog pricing and inventory stock are re-derived fresh from database state before payment.
            </p>
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-white/95 rounded-2xl p-5 sm:p-6 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-[#F0FDF4] text-verified flex items-center justify-center border border-[#BBF7D0]">
              <CreditCard className="w-5 h-5 text-verified" />
            </div>
            <span className="text-[10px] font-inter font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#F0FDF4] text-verified border border-[#BBF7D0]">
              Idempotent
            </span>
          </div>
          <div>
            <div className="text-[10px] font-inter font-semibold uppercase tracking-wider text-on-surface-variant/70 mb-0.5">
              Invariant Layer 03
            </div>
            <h3 className="font-outfit font-bold text-primary text-base sm:text-lg mb-1">
              Razorpay Execution
            </h3>
            <p className="font-inter text-xs text-on-surface-variant leading-relaxed">
              Atomic budget reservation, row locks, and replay defense ensure idempotent, verifiable settlement.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
