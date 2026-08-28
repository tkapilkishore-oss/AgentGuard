import React from 'react';
import { ViewTransitionWrapper } from '../components/ViewTransitionWrapper';
import { LiveDefenseWorkspace } from '../features/defense/LiveDefenseWorkspace';

export const LiveProtectionView: React.FC = () => {
  return (
    <ViewTransitionWrapper className="flex flex-col min-h-[calc(100vh-180px)]">
      <LiveDefenseWorkspace />
    </ViewTransitionWrapper>
  );
};
