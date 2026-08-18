const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

export function IconLogo({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base} strokeWidth={1.9}>
      <path d="M4 7h7M4 12h12M4 17h7" />
      <circle cx="18.5" cy="7" r="2" />
      <circle cx="18.5" cy="17" r="2" />
    </svg>
  )
}

export function IconDatabase({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <ellipse cx="12" cy="6" rx="7.5" ry="3" />
      <path d="M4.5 6v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6" />
      <path d="M4.5 12v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6" />
    </svg>
  )
}

export function IconClock({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </svg>
  )
}

export function IconPlus({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function IconPulse({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />
    </svg>
  )
}

export function IconSearch({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  )
}

export function IconRefresh({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M20 11a8 8 0 0 0-13.7-5.4L3 8.7" />
      <path d="M4 13a8 8 0 0 0 13.7 5.4L21 15.3" />
      <path d="M3 4.5v4.2h4.2M21 19.5v-4.2h-4.2" />
    </svg>
  )
}

export function IconPlay({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M7 5.5 18.5 12 7 18.5V5.5Z" />
    </svg>
  )
}

export function IconExternal({ size = 13 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M13.5 5H19v5.5M19 5l-8 8" />
      <path d="M18 14.5V18a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18V7.5A1.5 1.5 0 0 1 6 6h3.5" />
    </svg>
  )
}

export function IconCheck({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  )
}

export function IconAlert({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 4.5 21 20H3l9-15.5Z" />
      <path d="M12 10v4M12 17h.01" />
    </svg>
  )
}

export function IconClose({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  )
}

/* pipeline stage glyphs */

export function IconDownload({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 4v10" />
      <path d="m8 10.5 4 4 4-4" />
      <path d="M4.5 18.5h15" />
    </svg>
  )
}

export function IconBraces({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M9 4.5c-2 0-2.5 1-2.5 2.5v2c0 1.5-.7 2.4-2 3 1.3.6 2 1.5 2 3v2c0 1.5.5 2.5 2.5 2.5" />
      <path d="M15 4.5c2 0 2.5 1 2.5 2.5v2c0 1.5.7 2.4 2 3-1.3.6-2 1.5-2 3v2c0 1.5-.5 2.5-2.5 2.5" />
    </svg>
  )
}

export function IconLayers({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="m12 3.5 8 4.2-8 4.3-8-4.3 8-4.2Z" />
      <path d="m4 13 8 4.3 8-4.3" />
    </svg>
  )
}

export function IconShield({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 3.5 19 6v6c0 4-3 7-7 8.5C8 19 5 16 5 12V6l7-2.5Z" />
      <path d="m9.2 12 2 2 3.6-3.8" />
    </svg>
  )
}

export function IconCopy({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M15 6.5A2.5 2.5 0 0 0 12.5 4h-6A2.5 2.5 0 0 0 4 6.5v6A2.5 2.5 0 0 0 6.5 15" />
    </svg>
  )
}

export function IconSave({ size = 17 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M5 5h11l3 3v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" />
      <path d="M8 5v5h7M8 19v-5h8v5" />
    </svg>
  )
}
