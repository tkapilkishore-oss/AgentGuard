import React from 'react';
import { UntrustedClientChamber } from './UntrustedClientChamber';
import { FirewallInspectionHero } from './FirewallInspectionHero';

export const LiveDefenseWorkspace: React.FC = () => {
  return (
    <div className="py-8 sm:py-12 px-4 sm:px-6 max-w-7xl mx-auto w-full">
      {/* Header / Subheading */}
      <div className="text-center max-w-3xl mx-auto mb-10">
        <div className="flex items-center justify-center gap-2 mb-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-error opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-error"></span>
          </span>
          <span className="text-xs font-inter uppercase tracking-wider text-error font-semibold bg-error-container/40 px-3 py-0.5 rounded-full border border-error-container">
            Live Protection Active
          </span>
        </div>
        <h1 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-extrabold text-primary mb-3">
          The Transaction Machine
        </h1>
        <p className="font-inter text-sm sm:text-base text-on-surface-variant leading-relaxed">
          Submit untrusted claims on the left to observe how the server-authoritative firewall verifies claims against PostgreSQL catalog truth and executes payment on Razorpay.
        </p>
      </div>

      {/* Responsive Workspace Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 w-full items-stretch">
        {/* Left Column: Untrusted Agent Chamber (5 cols on xl) */}
        <div className="xl:col-span-5 flex flex-col">
          <UntrustedClientChamber />
        </div>

        {/* Right Column: Firewall Core & Authoritative Execution (7 cols on xl) */}
        <div className="xl:col-span-7 flex flex-col">
          <FirewallInspectionHero />
        </div>
      </div>
    </div>
  );
};
