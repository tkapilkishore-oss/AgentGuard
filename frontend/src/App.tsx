import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AgentGuardProvider } from './context/AgentGuardContext';
import { SecurityCockpitHeader } from './features/cockpit/SecurityCockpitHeader';
import { HomeView } from './views/HomeView';
import { LiveProtectionView } from './views/LiveProtectionView';
import { ThreatLabView } from './views/ThreatLabView';
import { ForensicLedgerView } from './views/ForensicLedgerView';
import { ConversationalVoiceDrawer } from './features/conversational/ConversationalVoiceDrawer';
import { DeveloperWireDrawer } from './features/telemetry/DeveloperWireDrawer';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AgentGuardProvider>
        <div className="min-h-screen flex flex-col font-inter selection:bg-lavender-tint selection:text-primary relative overflow-x-hidden">
          {/* Global Floating Security Cockpit Navigation */}
          <SecurityCockpitHeader />

          {/* Dedicated View Routing Area */}
          <main className="flex-1 w-full">
            <Routes>
              <Route path="/" element={<HomeView />} />
              <Route path="/live" element={<LiveProtectionView />} />
              <Route path="/threats" element={<ThreatLabView />} />
              <Route path="/forensics" element={<ForensicLedgerView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Global Multi-View Footer */}
          <footer className="w-full py-12 px-4 sm:px-8 border-t border-surface-container bg-white/80 backdrop-blur-sm flex flex-col md:flex-row justify-between items-center gap-6 text-xs text-on-surface-variant font-inter mt-auto">
            <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-center sm:text-left">
              <Link to="/" className="font-outfit font-extrabold text-primary text-base hover:opacity-80 transition-opacity">
                AgentGuard
              </Link>
              <span className="text-on-surface-variant text-xs">
                © 2024 AgentGuard AI Security. The definitive trust layer for autonomous commerce.
              </span>
            </div>

            <div className="flex gap-6 font-medium text-on-surface-variant text-xs">
              <Link to="/live" className="hover:text-primary transition-colors">
                Live Protection
              </Link>
              <Link to="/threats" className="hover:text-primary transition-colors">
                Threat Lab
              </Link>
              <Link to="/forensics" className="hover:text-primary transition-colors">
                Forensic Ledger
              </Link>
            </div>
          </footer>

          {/* Conversational Assistant Sliding Shell */}
          <ConversationalVoiceDrawer />

          {/* Collapsible Wire Protocol Telemetry Drawer */}
          <DeveloperWireDrawer />
        </div>
      </AgentGuardProvider>
    </BrowserRouter>
  );
};

export default App;
