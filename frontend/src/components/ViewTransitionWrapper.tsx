import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

interface ViewTransitionWrapperProps {
  children: React.ReactNode;
  className?: string;
}

export const ViewTransitionWrapper: React.FC<ViewTransitionWrapperProps> = ({
  children,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    if (containerRef.current) {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
      );
    }
  }, []);

  return (
    <div ref={containerRef} className={`w-full ${className}`}>
      {children}
    </div>
  );
};
