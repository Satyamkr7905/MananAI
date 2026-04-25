/**
 * Central tokens used across the UI — keep magic strings here so a single
 * edit ripples everywhere.
 */

export const STORAGE_KEYS = {
  token: "adt.token",
  user: "adt.user",
  pendingEmail: "adt.pendingEmail",
};

// Semantic color for error buckets. Charts and pills read from here.
export const ERROR_COLORS = {
  off_by_one: "#f59e0b",           // amber
  logic: "#ef4444",                // red
  time_complexity_issue: "#6366f1", // indigo
  base_case_issue: "#10b981",      // emerald
  null_handling: "#64748b",        // slate
  unknown: "#94a3b8",              // slate-400
};

export const ERROR_LABELS = {
  off_by_one: "Off-by-one",
  logic: "Logic",
  time_complexity_issue: "Time complexity",
  base_case_issue: "Base case",
  null_handling: "Null handling",
  unknown: "Unknown",
};

export const TOPIC_ICONS = {
  arrays: "Layers",
  dp: "Network",
  graphs: "GitBranch",
  trees: "TreePine",
  strings: "Type",
  default: "Circle",
};
