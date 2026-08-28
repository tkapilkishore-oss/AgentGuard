import React from 'react';
import { ViewTransitionWrapper } from '../components/ViewTransitionWrapper';
import { ThreatSimulationLab } from '../features/threat/ThreatSimulationLab';

export const ThreatLabView: React.FC = () => {
  return (
    <ViewTransitionWrapper className="flex flex-col min-h-[calc(100vh-180px)]">
      <ThreatSimulationLab />
    </ViewTransitionWrapper>
  );
};
