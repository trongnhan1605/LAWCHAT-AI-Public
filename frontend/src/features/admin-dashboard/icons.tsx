export function MenuIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M7 7L17 17M17 7L7 17" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

export function EditIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4.75 19.25h3.5l9.4-9.4-3.5-3.5-9.4 9.4v3.5Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M13.65 6.35l3.5 3.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

export function DeleteIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M5.5 7.25h13" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M9.5 10.75v5.5M14.5 10.75v5.5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M7.25 7.25l.9 11h7.7l.9-11M9 7.25l.85-1.5h4.3L15 7.25" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

export function ArrowRightIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M5 12h14" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
      <path d="M13 6l6 6-6 6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  );
}

export function StackIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M12 4 4 8l8 4 8-4-8-4Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="m4 12 8 4 8-4" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="m4 16 8 4 8-4" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

export function ChunkIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <rect height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8" width="14" x="5" y="4.5" />
      <rect height="5" rx="1.5" stroke="currentColor" strokeWidth="1.8" width="14" x="5" y="14.5" />
      <path d="M9 9.5v5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M15 9.5v5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

export function StructureIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M7 5h10" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M7 12h6" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M7 19h3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <circle cx="17.5" cy="12" fill="currentColor" r="1.5" />
      <circle cx="12.5" cy="19" fill="currentColor" r="1.5" />
    </svg>
  );
}

export function RelationIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <circle cx="7" cy="7" r="2.5" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="17" cy="17" r="2.5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9.2 8.8 14.8 15.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M14.4 8.2h4.1v4.1" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M18.5 8.2 12.7 14" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

export function AddIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

export function DownloadIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M12 4.5v8.75" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M8.75 10.75 12 14l3.25-3.25" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      <path d="M5.5 18.5h13" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

export function FilterIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M4 6h16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
      <path d="M7 12h10" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
      <path d="M10 18h4" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
}

export function ExpandIcon({ expanded }: { expanded: boolean }) {
  return expanded ? (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M6.5 14.25 12 8.75l5.5 5.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  ) : (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path d="M6.5 9.75 12 15.25l5.5-5.5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}
