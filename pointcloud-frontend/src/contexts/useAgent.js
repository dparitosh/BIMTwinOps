import { useContext } from 'react';
import { AgentContext } from './AgentContextDef';

export function useAgent() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgent must be used within AgentProvider');
  }
  return context;
}
