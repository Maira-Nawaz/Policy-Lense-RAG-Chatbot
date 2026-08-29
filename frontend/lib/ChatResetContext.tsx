"use client";

import { createContext, ReactNode, useCallback, useContext, useState } from "react";

function newConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Owns two closely related things:
 *
 * 1. "New chat" needs to clear state that lives inside the chat page
 *    component -- but clicking it while already on that page doesn't remount
 *    anything, so a plain <Link href="/"> alone wouldn't reset it.
 *    `resetToken` is the bridge: bump it, the chat page watches it and clears
 *    its exchanges whenever it changes.
 * 2. `activeConversationId` -- every /query call is tagged with whichever
 *    conversation_id is "active" so the backend can group them into one
 *    thread. A fresh one is generated on load and on every "New chat"; the
 *    sidebar can also point it at an existing conversation (via
 *    setActiveConversationId) when the user opens a past thread, so a
 *    follow-up question continues that thread instead of starting a new one.
 */
interface ChatResetContextValue {
  resetToken: number;
  activeConversationId: string;
  startNewChat: () => void;
  setActiveConversationId: (conversationId: string) => void;
}

const ChatResetContext = createContext<ChatResetContextValue>({
  resetToken: 0,
  activeConversationId: "",
  startNewChat: () => {},
  setActiveConversationId: () => {},
});

export function ChatResetProvider({ children }: { children: ReactNode }) {
  const [resetToken, setResetToken] = useState(0);
  const [activeConversationId, setActiveConversationIdState] = useState(newConversationId);

  const startNewChat = useCallback(() => {
    setResetToken((token) => token + 1);
    setActiveConversationIdState(newConversationId());
  }, []);

  const setActiveConversationId = useCallback((conversationId: string) => {
    setActiveConversationIdState(conversationId);
  }, []);

  return (
    <ChatResetContext.Provider
      value={{ resetToken, activeConversationId, startNewChat, setActiveConversationId }}
    >
      {children}
    </ChatResetContext.Provider>
  );
}

export function useChatReset() {
  return useContext(ChatResetContext);
}
