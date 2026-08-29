// Small inline icon set shared across the new nav/menu/sidebar chrome.
// Same stroke style as ThumbIcon.tsx (viewBox 0 0 24 24, currentColor, 1.5 stroke)
// so everything reads as one consistent icon language.

type IconProps = { className?: string };

export function ChevronLeftIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
    </svg>
  );
}

export function ChevronRightIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
    </svg>
  );
}

export function PlusIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

export function SlidersIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.5 6h9.75M3.75 6h3.75m0 0a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0ZM3.75 18h9.75m6.75 0h-3.75m0 0a1.875 1.875 0 1 1 3.75 0 1.875 1.875 0 0 1-3.75 0ZM3.75 12h13.5m3-0h-3.75m0 0a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Z"
      />
    </svg>
  );
}

export function ClockIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2" />
      <circle cx="12" cy="12" r="9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ChartBarIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v16.5h16.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15.75V12M12 15.75V8.25M16.5 15.75v-4.5" />
    </svg>
  );
}

// Sidebar logo mark -- a shield-with-checkmark, chosen over a generic
// "AI sparkle" glyph to read as policy/compliance rather than an AI wrapper.
export function ShieldCheckIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3.25 5.25 5.75v5.5c0 4.5 3 7.75 6.75 9.5 3.75-1.75 6.75-5 6.75-9.5v-5.5L12 3.25Z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="m9.25 12.25 1.9 1.9 3.6-3.9" />
    </svg>
  );
}

// Sidebar-footer account trigger -- a horizontal "more" glyph, ChatGPT-style.
export function DotsHorizontalIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <circle cx="5" cy="12" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="19" cy="12" r="1.5" />
    </svg>
  );
}

export function SearchIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <circle cx="10.5" cy="10.5" r="6.75" />
      <path strokeLinecap="round" d="m20.25 20.25-4.5-4.5" />
    </svg>
  );
}

// Map-pin style glyph -- reads clearly as "pin this" without needing an exact
// thumbtack shape.
export function PinIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21s7.5-6.5 7.5-11.25a7.5 7.5 0 1 0-15 0C4.5 14.5 12 21 12 21Z" />
      <circle cx="12" cy="9.75" r="2.25" />
    </svg>
  );
}

export function ShareIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5 12 3m0 0 4.5 4.5M12 3v13.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 16.5v3a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5v-3" />
    </svg>
  );
}

export function ArchiveIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M4.5 6.75v11.25a1.5 1.5 0 0 0 1.5 1.5h12a1.5 1.5 0 0 0 1.5-1.5V6.75M9.75 6.75V4.5a1.5 1.5 0 0 1 1.5-1.5h1.5a1.5 1.5 0 0 1 1.5 1.5v2.25" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 12h4.5" />
    </svg>
  );
}

export function FlagIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 3v18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 4.5h13.5l-2.25 3.75 2.25 3.75H4.5Z" />
    </svg>
  );
}

export function TrashIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5.25 6.75h13.5M9.75 6.75V4.5a1.5 1.5 0 0 1 1.5-1.5h1.5a1.5 1.5 0 0 1 1.5 1.5v2.25m-8.25 0 .75 12.75a1.5 1.5 0 0 0 1.5 1.35h6a1.5 1.5 0 0 0 1.5-1.35l.75-12.75"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 10.5v6M13.5 10.5v6" />
    </svg>
  );
}

export function CopyIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <rect x="8.25" y="8.25" width="12" height="12" rx="1.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 8.25V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8.25A1.5 1.5 0 0 0 6 15.75h2.25" />
    </svg>
  );
}

export function RetryIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12a7.5 7.5 0 0 1 13.5-4.5M19.5 12a7.5 7.5 0 0 1-13.5 4.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 4.5v3.75h-3.75M6 19.5v-3.75h3.75" />
    </svg>
  );
}
