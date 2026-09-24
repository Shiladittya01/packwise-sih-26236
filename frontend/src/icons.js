const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/><path d="m20 2 .5 1.5L22 4l-1.5.5L20 6l-.5-1.5L18 4l1.5-.5L20 2Z"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8l10-5Z"/><path d="m2 12 10 5 10-5M2 16l10 5 10-5"/>',
  book: '<path d="M12 5v16M12 5C8 2 4 3 2 4v16c3-1 7-1 10 1 3-2 7-2 10-1V4c-2-1-6-2-10 1Z"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  leaf: '<path d="M20 3C9 1 2 7 5 15s15 5 15-12Z"/><path d="M3 22 14 10"/>',
  shield: '<path d="m12 3 9 4v6c0 4-5 7-9 9-4-2-9-5-9-9V7l9-4Z"/><path d="m8 12 3 3 5-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon: '<path d="M21 14A9 9 0 0 1 10 3a9 9 0 1 0 11 11Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
  print: '<path d="M6 8V3h12v5M6 17H3V9h18v8h-3M6 14h12v7H6zM17 11h1"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7a3.5 3.5 0 0 0-5-5L4 14l-1 7Z"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  flask: '<path d="M8 3h8M9 3v7L3 20c-.4.7.2 1 1 1h16c.8 0 1.4-.3 1-1l-6-10V3M6 16h12"/>',
  chart: '<path d="M4 3v17h17M8 15l4-5 4 2 5-7"/>',
  truck: '<path d="M2 5h12v12H2zM14 9h4l4 4v4h-8"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  thermometer: '<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z"/><path d="M12 10v8"/>',
  drop: '<path d="M12 2C9 7 4 11 4 15a8 8 0 0 0 16 0c0-4-5-8-8-13Z"/>',
  wind: '<path d="M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3"/>',
  recycle: '<path d="m8 5 3-3 5 8M16 5v5h-5M19 11l3 6-3 4h-7m4-4-4 4 4 3M8 21H3l-2-4 5-8M1 10l5-1 1 5"/>',
  bolt: '<path d="m13 2-9 12h7l-1 8 10-13h-7l1-7Z"/>',
  external: '<path d="M14 3h7v7M21 3 10 14M10 4H3v17h17v-7"/>'
};
export function icon(name, size = 20) { return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.layers}</svg>`; }
export function foodArt(kind, size = 64) {
  const art = {
    tomato: '<ellipse cx="33" cy="38" rx="22" ry="20" fill="#e4664e"/><ellipse cx="40" cy="35" rx="15" ry="18" fill="#ef7c5b"/><path d="m32 23-14-9 11 2 3-10 4 11 11-4-8 10" fill="#51754c"/><path d="M18 33c-3 4-3 7-2 9" stroke="#ffb398" stroke-width="3" fill="none" stroke-linecap="round"/>',
    chips: '<path d="m17 13 32 2-3 40-34-2Z" fill="#daa246"/><path d="m20 11 28 2 1 6-32-2Z" fill="#f1be66"/><path d="m14 49 33 2-1 5-34-2Z" fill="#c18a37"/><ellipse cx="31" cy="33" rx="12" ry="10" fill="#fff0bc"/><path d="M24 29c6-3 11-1 13 5M24 34c3-2 7-1 9 2" stroke="#d9aa50" fill="none" stroke-width="2"/>',
    biscuit: '<circle cx="27" cy="36" r="22" fill="#bd8651"/><circle cx="36" cy="28" r="22" fill="#e2b77d" stroke="#cd9c61" stroke-width="2" stroke-dasharray="2 3"/><g fill="#956038"><circle cx="28" cy="18" r="2.5"/><circle cx="40" cy="17" r="2"/><circle cx="25" cy="29" r="2"/><circle cx="37" cy="29" r="3"/><circle cx="47" cy="26" r="2"/><circle cx="33" cy="40" r="2"/><circle cx="45" cy="38" r="2.5"/></g>',
    milk: '<path d="M20 7h22v9l5 8v34H15V24l5-8Z" fill="#f5fafb" stroke="#a4c6d8" stroke-width="2"/><path d="M20 7h22v8H20zM15 29h32v18H15z" fill="#91bed1"/><path d="M32 32c-3 4-6 6-6 9a6 6 0 0 0 12 0c0-3-3-5-6-9" fill="#f7fcff"/>',
    snow: '<path d="m14 14 38 4-5 37-39-5Z" fill="#8fb6a2"/><path d="m14 10 39 5-1 7-39-5ZM9 47l39 5-1 6-39-5Z" fill="#b0cfbd"/><g stroke="#eff9f0" stroke-width="2.5" stroke-linecap="round"><path d="M31 24v23M21 30l20 11M21 41l20-11M28 26l3 3 3-3M28 44l3-3 3 3"/></g>',
    grain: '<path d="m19 15 25 1 10 32q2 11-20 11T10 48Z" fill="#b5a584"/><path d="M20 14 15 6l15 3 10-5 6 12" fill="#c9b99a"/><path d="m20 17 25 1" stroke="#806e56" stroke-width="3"/><path d="M18 30h27v18H18z" fill="#e5dcc7"/><path d="M32 45V32m0 5c-6 0-6-4-6-4 6 0 6 4 6 4Zm0 4c6 0 6-4 6-4-6 0-6 4-6 4Z" stroke="#7f8f62" fill="#7f8f62"/>'
  };
  return `<svg width="${size}" height="${size}" viewBox="0 0 64 64" fill="none" aria-hidden="true">${art[kind] || art.grain}</svg>`;
}
export const brandMark = '<svg width="35" height="35" viewBox="0 0 40 40" aria-hidden="true"><rect width="40" height="40" rx="12" fill="currentColor"/><path d="M11 28V13h8c8 0 12 9 3 13h-5v-7h4" fill="none" stroke="var(--logo-leaf, #d4eda8)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M26 9c-7-1-9 2-8 6 5 1 8-1 8-6" fill="var(--logo-leaf, #d4eda8)"/></svg>';
