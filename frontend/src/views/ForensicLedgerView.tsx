import React from 'react';
import { ViewTransitionWrapper } from '../components/ViewTransitionWrapper';
import { ForensicLedger } from '../features/forensics/ForensicLedger';

export const ForensicLedgerView: React.FC = () => {
  return (
    <ViewTransitionWrapper className="flex flex-col min-h-[calc(100vh-180px)]">
      <ForensicLedger />
    </ViewTransitionWrapper>
  );
};
