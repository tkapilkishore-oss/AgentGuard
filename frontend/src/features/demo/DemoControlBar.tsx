/**
 * DemoControlBar.tsx — Autonomous Demo Mode Control Panel
 *
 * Compact, floating glassmorphism control bar displaying:
 *  - ● AGENT DEMO MODE status with pulsing indicator
 *  - Step progression: Cockpit → Defense → Attack → Decision → Forensics
 *  - Spoken narration caption text
 *  - Interactive [ Pause ] / [ Play ] and [ Stop ] controls
 */

import React from 'react';
import { Play, Pause, Square, Sparkles } from 'lucide-react';
import { useAutonomousDemo } from './AutonomousDemoContext';

export const DemoControlBar: React.FC = () => {
  const { demoState, currentStepId, isPaused, currentNarration, pauseDemo, resumeDemo, stopDemo } =
    useAutonomousDemo();

  // Show only during RUNNING or PAUSED demo modes
  if (demoState !== 'RUNNING' && demoState !== 'PAUSED') {
    return null;
  }

  const steps = [
    { label: 'Cockpit', activeAt: [1, 2] },
    { label: 'Defense', activeAt: [3] },
    { label: 'Threat Lab', activeAt: [4] },
    { label: 'Attack & Denial', activeAt: [5, 6, 7] },
    { label: 'Legitimate & Approval', activeAt: [8, 9, 10] },
    { label: 'Summary', activeAt: [11] },
  ];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9990] w-11/12 max-w-xl mx-auto font-inter">
      <div className="bg-white/95 backdrop-blur-xl border border-surface-container-high rounded-2xl shadow-ambient-3 p-4 sm:p-5 flex flex-col gap-3 transition-all duration-300">
        {/* Header Row: Indicator & Controls */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isPaused ? 'bg-escalation' : 'bg-primary'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  isPaused ? 'bg-escalation' : 'bg-primary'
                }`}
              />
            </span>
            <span className="font-outfit font-extrabold text-xs sm:text-sm text-primary uppercase tracking-wider flex items-center gap-1.5">
              <span>Agent Demo Mode</span>
              <span className="text-[10px] font-semibold text-on-surface-variant font-inter lowercase">
                ({isPaused ? 'paused' : 'autonomous'})
              </span>
            </span>
          </div>

          {/* Action Buttons: Pause / Play & Stop */}
          <div className="flex items-center gap-2">
            {isPaused ? (
              <button
                onClick={resumeDemo}
                className="h-8 px-3.5 bg-primary hover:bg-secondary text-white rounded-full font-inter text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 active:scale-95"
                title="Resume Walkthrough"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Play</span>
              </button>
            ) : (
              <button
                onClick={pauseDemo}
                className="h-8 px-3.5 bg-surface-container hover:bg-surface-container-high text-primary rounded-full font-inter text-xs font-bold transition-all border border-surface-container-high flex items-center gap-1.5 active:scale-95"
                title="Pause Walkthrough"
              >
                <Pause className="w-3 h-3 fill-current" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={stopDemo}
              className="h-8 px-3.5 bg-error-container/60 hover:bg-error-container text-error rounded-full font-inter text-xs font-bold transition-all border border-error-container flex items-center gap-1.5 active:scale-95"
              title="Stop Walkthrough"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>Stop</span>
            </button>
          </div>
        </div>

        {/* Step Progress Indicators */}
        <div className="flex items-center justify-between gap-1 sm:gap-1.5 pt-1">
          {steps.map((s) => {
            const isCurrent = s.activeAt.includes(currentStepId);
            const isPast = Math.max(...s.activeAt) < currentStepId;

            return (
              <div key={s.label} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`h-1.5 w-full rounded-full transition-all duration-300 ${
                    isCurrent
                      ? 'bg-primary shadow-sm'
                      : isPast
                      ? 'bg-verified'
                      : 'bg-surface-container'
                  }`}
                />
                <span
                  className={`text-[10px] font-semibold truncate ${
                    isCurrent
                      ? 'text-primary font-bold'
                      : isPast
                      ? 'text-on-surface-variant'
                      : 'text-outline'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Narration Caption Box */}
        {currentNarration && (
          <div className="px-3 py-2 bg-surface-container-low rounded-xl border border-surface-container text-xs text-on-surface font-inter flex items-start gap-2 leading-relaxed">
            <Sparkles className="w-3.5 h-3.5 text-primary flex-shrink-0 mt-0.5" />
            <p className="line-clamp-2">{currentNarration}</p>
          </div>
        )}
      </div>
    </div>
  );
};
