/**
 * DemoControlBar.tsx — Autonomous Demo Mode Control Panel
 *
 * Floating subtle glassmorphic control bar displaying:
 *  - Status with subtle pulsing indicator
 *  - Compact step progression: Cockpit → Defense → Threat Lab → Attack & Denial → Legitimate & Approval → Summary
 *  - Spoken narration live rolling caption text
 *  - Interactive [ Pause ] / [ Play ] and [ Stop ] controls
 *
 * Styled for subtle presence that doesn't compete with the demonstrated UI.
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
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[9990] w-11/12 max-w-lg mx-auto font-inter pointer-events-auto">
      <div className="bg-white/40 sm:bg-white/35 hover:bg-white/80 backdrop-blur-xl border border-white/50 hover:border-white/80 rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.04)] p-3 sm:p-3.5 flex flex-col gap-2 transition-all duration-300">
        {/* Header Row: Status & Controls */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${
                  isPaused ? 'bg-escalation' : 'bg-primary'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  isPaused ? 'bg-escalation' : 'bg-primary'
                }`}
              />
            </span>
            <span className="font-outfit font-bold text-xs text-primary uppercase tracking-wider flex items-center gap-1.5 opacity-80">
              <span>Agent Demo Mode</span>
              <span className="text-[10px] font-medium text-on-surface-variant font-inter lowercase">
                ({isPaused ? 'paused' : 'autonomous'})
              </span>
            </span>
          </div>

          {/* Action Buttons: Pause / Play & Stop */}
          <div className="flex items-center gap-1.5">
            {isPaused ? (
              <button
                onClick={resumeDemo}
                className="h-7 px-3 bg-primary/90 hover:bg-primary text-white rounded-full font-inter text-xs font-semibold transition-all shadow-xs flex items-center gap-1.5 active:scale-95 cursor-pointer"
                title="Resume Walkthrough"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Play</span>
              </button>
            ) : (
              <button
                onClick={pauseDemo}
                className="h-7 px-3 bg-white/50 hover:bg-white text-primary rounded-full font-inter text-xs font-semibold transition-all border border-white/60 hover:border-surface-container flex items-center gap-1.5 active:scale-95 cursor-pointer shadow-xs"
                title="Pause Walkthrough"
              >
                <Pause className="w-3 h-3 fill-current" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={stopDemo}
              className="h-7 px-3 bg-error-container/30 hover:bg-error-container/70 text-error rounded-full font-inter text-xs font-semibold transition-all border border-error-container/40 flex items-center gap-1.5 active:scale-95 cursor-pointer"
              title="Stop Walkthrough"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>Stop</span>
            </button>
          </div>
        </div>

        {/* Step Progress Indicators */}
        <div className="flex items-center justify-between gap-1 sm:gap-1.5 pt-0.5">
          {steps.map((s) => {
            const isCurrent = s.activeAt.includes(currentStepId);
            const isPast = Math.max(...s.activeAt) < currentStepId;

            return (
              <div key={s.label} className="flex-1 flex flex-col items-center gap-0.5">
                <div
                  className={`h-1 w-full rounded-full transition-all duration-300 ${
                    isCurrent
                      ? 'bg-primary'
                      : isPast
                      ? 'bg-verified/80'
                      : 'bg-surface-container/40'
                  }`}
                />
                <span
                  className={`text-[9px] sm:text-[10px] font-medium truncate ${
                    isCurrent
                      ? 'text-primary font-bold'
                      : isPast
                      ? 'text-on-surface-variant/75'
                      : 'text-outline/50'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Live Rolling Caption Box */}
        {currentNarration && (
          <div className="px-3 py-1.5 bg-white/40 rounded-xl border border-white/50 text-xs text-on-surface font-inter flex items-start gap-2 leading-relaxed backdrop-blur-xs">
            <Sparkles className="w-3.5 h-3.5 text-primary/70 flex-shrink-0 mt-0.5" />
            <p className="line-clamp-2 transition-all duration-150 font-medium">{currentNarration}</p>
          </div>
        )}
      </div>
    </div>
  );
};
