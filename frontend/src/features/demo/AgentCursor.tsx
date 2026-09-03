/**
 * AgentCursor.tsx — Visual Agent Cursor Overlay
 *
 * Renders a high-tech, responsive cursor that visually tracks semantic targets
 * (data-agent-target) on the screen.
 *
 * Uses hardware-accelerated CSS transforms and getBoundingClientRect() to remain
 * rock-solid across all viewport sizes (390px mobile to 1440px+ desktop).
 */

import React, { useState, useEffect, useRef } from 'react';
import { useAutonomousDemo } from './AutonomousDemoContext';

export const AgentCursor: React.FC = () => {
  const { demoState, currentTargetId } = useAutonomousDemo();

  const [coords, setCoords] = useState<{ x: number; y: number } | null>(null);
  const [isVisible, setIsVisible] = useState<boolean>(false);
  const [isClicking, setIsClicking] = useState<boolean>(false);
  const rafIdRef = useRef<number | null>(null);

  // Active only during RUNNING or PAUSED demo states
  const isActive = (demoState === 'RUNNING' || demoState === 'PAUSED') && currentTargetId !== null;

  useEffect(() => {
    if (!isActive || !currentTargetId) {
      setIsVisible(false);
      return;
    }

    const updatePosition = () => {
      const element = document.querySelector(`[data-agent-target="${currentTargetId}"]`);
      if (element) {
        // Smooth scroll if element is not well-centered in viewport
        const rect = element.getBoundingClientRect();
        const isInViewport =
          rect.top >= 0 &&
          rect.left >= 0 &&
          rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
          rect.right <= (window.innerWidth || document.documentElement.clientWidth);

        if (!isInViewport) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // Recompute position to target center
        const targetRect = element.getBoundingClientRect();
        const targetX = targetRect.left + targetRect.width / 2;
        const targetY = targetRect.top + targetRect.height / 2;

        setCoords({ x: targetX, y: targetY });
        setIsVisible(true);

        // Visual click indication
        setIsClicking(true);
        const clickTimer = window.setTimeout(() => setIsClicking(false), 500);
        return () => window.clearTimeout(clickTimer);
      } else {
        // Element not yet mounted/visible
        setIsVisible(false);
      }
    };

    // Initial position lookup with short delay for DOM mount
    const timer = window.setTimeout(updatePosition, 250);

    // Event listeners for window resize & scroll
    const handleScrollOrResize = () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = requestAnimationFrame(updatePosition);
    };

    window.addEventListener('resize', handleScrollOrResize, { passive: true });
    window.addEventListener('scroll', handleScrollOrResize, { passive: true });

    return () => {
      window.clearTimeout(timer);
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      window.removeEventListener('resize', handleScrollOrResize);
      window.removeEventListener('scroll', handleScrollOrResize);
    };
  }, [isActive, currentTargetId]);

  if (!isActive || !isVisible || !coords) return null;

  return (
    <div
      className="fixed top-0 left-0 pointer-events-none z-[9999] transition-transform duration-500 ease-out will-change-transform"
      style={{
        transform: `translate3d(${coords.x}px, ${coords.y}px, 0)`,
      }}
    >
      {/* Subtle click indicator ring */}
      {isClicking && (
        <span className="absolute -top-2 -left-2 w-7 h-7 rounded-full bg-primary/25 animate-ping pointer-events-none" />
      )}

      {/* Clean normal browser-style arrow pointer SVG */}
      <svg
        className={`w-5 h-5 -top-1 -left-1 relative drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)] transition-transform duration-150 ${
          isClicking ? 'scale-90 translate-y-0.5' : 'scale-100'
        }`}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M4.5 3.5V19.5L9.5 14.5H16.5L4.5 3.5Z"
          fill="#1E1B4B"
          stroke="#FFFFFF"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
};
