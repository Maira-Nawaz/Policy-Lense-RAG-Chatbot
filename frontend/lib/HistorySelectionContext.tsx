"use client";

import { createContext, ReactNode, useCallback, useContext, useState } from "react";
import type { HistoryItem } from "./types";

export interface PendingConversation {
  conversationId: string;
  messages: HistoryItem[];
}

/**
 * Bridges a sidebar conversation click to the chat page's own state.
 *
 * The sidebar now lives in the shared (app) layout, one level above the chat
 * page, so it can appear on /metrics too -- but only the chat page knows how
 * to turn fetched messages back into rendered exchanges. Clicking a
 * conversation sets `pendingConversation` here (and navigates to "/"); the
 * chat page watches it, renders the full thread, and clears it.
 */
interface HistorySelectionContextValue {
  pendingConversation: PendingConversation | null;
  selectConversation: (conversationId: string, messages: HistoryItem[]) => void;
  clearPendingConversation: () => void;
}

const HistorySelectionContext = createContext<HistorySelectionContextValue>({
  pendingConversation: null,
  selectConversation: () => {},
  clearPendingConversation: () => {},
});

export function HistorySelectionProvider({ children }: { children: ReactNode }) {
  const [pendingConversation, setPendingConversation] = useState<PendingConversation | null>(null);

  const selectConversation = useCallback((conversationId: string, messages: HistoryItem[]) => {
    setPendingConversation({ conversationId, messages });
  }, []);

  const clearPendingConversation = useCallback(() => setPendingConversation(null), []);

  return (
    <HistorySelectionContext.Provider
      value={{ pendingConversation, selectConversation, clearPendingConversation }}
    >
      {children}
    </HistorySelectionContext.Provider>
  );
}

export function useHistorySelection() {
  return useContext(HistorySelectionContext);
}
