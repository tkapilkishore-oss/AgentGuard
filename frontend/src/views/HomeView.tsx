import React from 'react';
import { ViewTransitionWrapper } from '../components/ViewTransitionWrapper';
import { HeroStorySection } from '../features/story/HeroStorySection';
import { TrustJourneyStorySection } from '../features/story/TrustJourneyStorySection';
import { FirewallThinkingSection } from '../features/story/FirewallThinkingSection';
import { FinalCtaSection } from '../features/story/FinalCtaSection';

export const HomeView: React.FC = () => {
  return (
    <ViewTransitionWrapper className="flex flex-col">
      {/* SECTION 01: HERO & VALUE PROPOSITION */}
      <HeroStorySection />

      {/* SECTION 02: THE TRUST JOURNEY PIPELINE */}
      <TrustJourneyStorySection />

      {/* SECTION 03: FIREWALL MECHANICS & INVARIANTS */}
      <FirewallThinkingSection />

      {/* SECTION 04: ACTION CTA BANNER */}
      <FinalCtaSection />
    </ViewTransitionWrapper>
  );
};
