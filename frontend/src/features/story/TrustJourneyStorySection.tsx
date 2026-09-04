import React, { useEffect, useRef } from 'react';
import {
  Bot,
  Shield,
  Database,
  CreditCard,
  CheckCircle2,
} from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export const TrustJourneyStorySection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const stepsContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const ctx = gsap.context(() => {
      if (stepsContainerRef.current?.children) {
        gsap.fromTo(
          Array.from(stepsContainerRef.current.children),
          { y: 30, opacity: 0, scale: 0.96 },
          {
            y: 0,
            opacity: 1,
            scale: 1,
            duration: 0.6,
            stagger: 0.12,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: stepsContainerRef.current,
              start: 'top 80%',
              toggleActions: 'play none none none',
            },
          }
        );
      }
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const steps = [
    {
      number: '01',
      title: 'AI Agent Claim',
      role: 'Untrusted Proposer',
      icon: <Bot className="w-6 h-6 text-error" />,
      tag: 'Zero Trust',
      tagColor: 'bg-error-container/40 text-error border-error-container',
      description:
        'The intelligent shopping agent formulates purchase intent. This payload carries zero authorization weight.',
      badgeBg: 'bg-error-container/30',
      borderColor: 'border-error-container/60',
    },
    {
      number: '02',
      title: 'AgentGuard Core',
      role: 'Deterministic Policy Gate',
      icon: <Shield className="w-6 h-6 text-white" />,
      tag: 'Deterministic',
      tagColor: 'bg-lavender-tint text-[#4C1D95] border-primary-fixed',
      description:
        'Evaluates mandate thresholds, merchant identity, and policy invariants purely on the server without LLM hallucination.',
      badgeBg: 'bg-primary text-white ring-4 ring-lavender-tint',
      borderColor: 'border-primary/40',
      isHero: true,
    },
    {
      number: '03',
      title: 'PostgreSQL Truth',
      role: 'Authoritative Financial Truth',
      icon: <Database className="w-6 h-6 text-secondary" />,
      tag: 'Source of Truth',
      tagColor: 'bg-secondary-fixed text-[#00346e] border-secondary-container',
      description:
        'Catalog prices and inventory stock are queried fresh from database rows. Tampered claimed prices are instantly rejected.',
      badgeBg: 'bg-secondary-fixed/50',
      borderColor: 'border-secondary-container',
    },
    {
      number: '04',
      title: 'Razorpay Execution',
      role: 'Idempotent Payment Settlement',
      icon: <CreditCard className="w-6 h-6 text-verified" />,
      tag: 'Verified Secure',
      tagColor: 'bg-[#F0FDF4] text-verified border-[#BBF7D0]',
      description:
        'Atomic budget reservation, row locks, and HMAC-signed Razorpay test payments prevent double-spending and race conditions.',
      badgeBg: 'bg-[#F0FDF4]',
      borderColor: 'border-[#BBF7D0]',
    },
  ];

  return (
    <section
      ref={sectionRef}
      id="trust-journey"
      className="py-16 sm:py-20 px-4 sm:px-6 max-w-7xl mx-auto w-full"
    >
      {/* Section Header */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="flex items-center justify-center gap-2 mb-3">
          <span className="text-xs font-inter uppercase tracking-wider text-primary font-bold bg-lavender-tint/70 px-3.5 py-1 rounded-full border border-primary-fixed">
            The Trust Journey Pipeline
          </span>
        </div>
        <h2 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary mb-4">
          The Secure Path to Execution
        </h2>
        <p className="font-inter text-sm sm:text-base text-on-surface-variant leading-relaxed">
          How AgentGuard safely converts untrusted AI intent into authoritative financial transactions across 4 rigorous verification gates.
        </p>
      </div>

      {/* 4 Pipeline Steps Grid with Animated Connection */}
      <div
        ref={stepsContainerRef}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative"
      >
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`rounded-2xl p-6 border transition-all duration-300 flex flex-col justify-between relative card-depth-hover ${
              step.isHero
                ? 'bg-primary text-white border-primary shadow-[0_4px_14px_rgba(59,7,100,0.18),0_14px_32px_rgba(59,7,100,0.14)] ring-4 ring-lavender-tint/80'
                : 'bg-white/95 text-on-surface border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)]'
            }`}
          >
            {/* Step Top Bar */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <span
                  className={`text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg ${
                    step.isHero ? 'bg-white/15 text-white' : 'bg-slate-100 text-on-surface-variant font-semibold'
                  }`}
                >
                  GATE {step.number}
                </span>

                <span
                  className={`px-2.5 py-0.5 text-xs font-inter font-semibold rounded-full border ${
                    step.isHero ? 'bg-white/20 text-white border-white/30' : step.tagColor
                  }`}
                >
                  {step.tag}
                </span>
              </div>

              {/* Icon & Title */}
              <div className="flex items-center gap-3 mb-3">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-xs ${
                    step.isHero ? 'bg-white/15 text-white' : step.badgeBg
                  }`}
                >
                  {step.icon}
                </div>
                <div>
                  <h3
                    className={`font-outfit font-bold text-lg leading-tight ${
                      step.isHero ? 'text-white' : 'text-primary'
                    }`}
                  >
                    {step.title}
                  </h3>
                  <span
                    className={`text-xs font-inter font-medium ${
                      step.isHero ? 'text-white/80' : 'text-on-surface-variant'
                    }`}
                  >
                    {step.role}
                  </span>
                </div>
              </div>

              {/* Description */}
              <p
                className={`font-inter text-xs leading-relaxed mt-2 ${
                  step.isHero ? 'text-white/90' : 'text-on-surface-variant'
                }`}
              >
                {step.description}
              </p>
            </div>

            {/* Bottom Status Callout */}
            <div
              className={`mt-5 pt-3.5 border-t text-xs font-inter flex items-center justify-between ${
                step.isHero
                  ? 'border-white/20 text-white/80'
                  : 'border-slate-100 text-on-surface-variant'
              }`}
            >
              <span className="text-[11px] uppercase tracking-wider font-semibold opacity-70">Enforcement:</span>
              <span className="font-semibold font-mono text-[11px]">
                {idx === 0
                  ? 'Candidate Only'
                  : idx === 1
                  ? 'Zero LLM Authority'
                  : idx === 2
                  ? 'Fresh DB Lookup'
                  : 'Atomic Lock'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* 3 Core Invariant Badges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 pt-6 border-t border-surface-container text-xs font-inter text-on-surface-variant">
        <div className="flex items-center gap-2.5 justify-center bg-white p-4 rounded-xl border border-surface-container shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
          <span><strong>Pure Policy Engine:</strong> Re-derives parameters deterministically</span>
        </div>
        <div className="flex items-center gap-2.5 justify-center bg-white p-4 rounded-xl border border-surface-container shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
          <span><strong>PostgreSQL Source of Truth:</strong> Zero client price manipulation</span>
        </div>
        <div className="flex items-center gap-2.5 justify-center bg-white p-4 rounded-xl border border-surface-container shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
          <span><strong>SHA-256 Audit Trail:</strong> Continuous tamper-evident cryptographic chain</span>
        </div>
      </div>
    </section>
  );
};
