/**
 * Small, dependency-free formatters used across the UI.
 * Keeping them here means components never sprinkle `toFixed` or `new Date()` logic.
 */

export const pct = (value, digits = 0) => {
  if (value == null || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(digits)}%`;
};

export const num = (value) => {
  if (value == null || Number.isNaN(value)) return "--";
  return Number(value).toLocaleString();
};

export const shortDate = (isoOrDate) => {
  const d = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  if (Number.isNaN(d.getTime())) return "--";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

export const relativeTime = (isoOrDate) => {
  const then = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  const diff = (Date.now() - then.getTime()) / 1000;
  if (Number.isNaN(diff)) return "";
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

export const capitalize = (s = "") => (s ? s[0].toUpperCase() + s.slice(1) : "");
