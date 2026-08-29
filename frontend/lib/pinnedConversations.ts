// Pin state lives in localStorage only -- there's no query_logs column for it
// (pinning is a personal UI preference, not worth a migration for). Keyed per
// user so a shared browser/profile can't leak one account's pins into
// another's view. Tradeoff: pins are per-browser, not synced across devices.

function storageKey(userId: string): string {
  return `policylens.pinned.${userId}`;
}

export function getPinnedIds(userId: string): string[] {
  try {
    const raw = window.localStorage.getItem(storageKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function isPinned(userId: string, conversationId: string): boolean {
  return getPinnedIds(userId).includes(conversationId);
}

export function togglePin(userId: string, conversationId: string): string[] {
  const current = getPinnedIds(userId);
  const next = current.includes(conversationId)
    ? current.filter((id) => id !== conversationId)
    : [...current, conversationId];
  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(next));
  } catch {
    // Storage unavailable (private window, quota, etc.) -- pin just won't persist.
  }
  return next;
}
