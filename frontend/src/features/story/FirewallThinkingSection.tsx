import React, { useEffect, useRef } from 'react';
import {
  Database,
  Lock,
  FileCode,
  Scale,
} from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export const FirewallThinkingSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const ctx = gsap.context(() => {
      if (cardsRef.current?.children) {
        gsap.fromTo(
          Array.from(cardsRef.current.children),
          { y: 28, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.55,
            stagger: 0.1,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: cardsRef.current,
              start: 'top 80%',
              toggleActions: 'play none none none',
            },
          }
        );
      }
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      id="firewall-thinking"
      className="py-16 sm:py-20 px-4 sm:px-6 max-w-7xl mx-auto w-full"
    >
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="flex items-center justify-center gap-2 mb-3">
          <span className="text-xs font-inter uppercase tracking-wider text-primary font-bold bg-lavender-tint/70 px-3.5 py-1 rounded-full border border-primary-fixed">
            Firewall Mechanics & Invariants
          </span>
        </div>
        <h2 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary mb-4">
          How the Firewall Thinks
        </h2>
        <p className="font-inter text-sm sm:text-base text-on-surface-variant leading-relaxed">
          The mathematical and architectural guarantees that ensure autonomous agent actions can never compromise ledger security.
        </p>
      </div>

      {/* 4 Architectural Invariants Grid */}
      <div
        ref={cardsRef}
        className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch"
      >
        {/* Invariant 1 */}
        <div className="bg-white/95 rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-error-container/40 text-error flex items-center justify-center border border-error-container/60 shadow-xs">
                <FileCode className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-error-container/30 text-error border border-error-container/40">
                INVARIANT 01
              </span>
            </div>

            <h3 className="font-outfit font-bold text-primary text-xl">
              Zero Prompt Authority
            </h3>
            <p className="font-inter text-sm text-on-surface-variant leading-relaxed">
              No matter what prompt injection or jailbreak an attacker feeds the shopping agent LLM, the output is treated strictly as a candidate claim with zero execution privilege.
            </p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/90 font-inter text-xs text-on-surface flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Defense Result:</span>
            <span className="font-semibold text-verified font-mono text-[11px]">LLM Hallucinations Neutralized</span>
          </div>
        </div>

        {/* Invariant 2 */}
        <div className="bg-white/95 rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-secondary-fixed text-secondary flex items-center justify-center border border-secondary-container/60 shadow-xs">
                <Database className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-secondary-fixed text-[#00346e] border border-secondary-container">
                INVARIANT 02
              </span>
            </div>

            <h3 className="font-outfit font-bold text-primary text-xl">
              PostgreSQL Catalog Truth
            </h3>
            <p className="font-inter text-sm text-on-surface-variant leading-relaxed">
              The proposal price is ignored during payment execution. The backend queries PostgreSQL fresh and charges only the verified catalog price.
            </p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/90 font-inter text-xs text-on-surface flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Defense Result:</span>
            <span className="font-semibold text-error font-mono text-[11px]">400 Bad Request / PRICE_MISMATCH</span>
          </div>
        </div>

        {/* Invariant 3 */}
        <div className="bg-white/95 rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-primary text-white flex items-center justify-center shadow-xs ring-4 ring-lavender-tint/80">
                <Lock className="w-6 h-6 text-white" />
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-lavender-tint text-[#4C1D95] border border-primary-fixed">
                INVARIANT 03
              </span>
            </div>

            <h3 className="font-outfit font-bold text-primary text-xl">
              Atomic Locks & Replay Defense
            </h3>
            <p className="font-inter text-sm text-on-surface-variant leading-relaxed">
              Every execution uses database row locking and unique idempotency keys. Re-submitting an already executed transaction is locked and safely halted.
            </p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/90 font-inter text-xs text-on-surface flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Defense Result:</span>
            <span className="font-semibold text-error font-mono text-[11px]">409 Conflict / REPLAY_DETECTED</span>
          </div>
        </div>

        {/* Invariant 4 */}
        <div className="bg-white/95 rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-[0_1px_3px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] card-depth-hover flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-[#F0FDF4] text-verified flex items-center justify-center border border-[#BBF7D0] shadow-xs">
                <Scale className="w-6 h-6 text-verified" />
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-[#F0FDF4] text-verified border border-[#BBF7D0]">
                INVARIANT 04
              </span>
            </div>

            <h3 className="font-outfit font-bold text-primary text-xl">
              Cryptographic Audit Chain
            </h3>
            <p className="font-inter text-sm text-on-surface-variant leading-relaxed">
              Every action from genesis to payment captures a SHA-256 hash linking to the previous event, forming a mathematically verifiable Merkle trace.
            </p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/90 font-inter text-xs text-on-surface flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Defense Result:</span>
            <span className="font-semibold text-verified font-mono text-[11px]">SHA-256 Tamper-Evident Chain</span>
          </div>
        </div>
      </div>
    </section>
  );
};
