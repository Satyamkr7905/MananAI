// shared tokens used across the UI — one place for magic strings.

export const STORAGE_KEYS = {
  token: "adt.token",
  user: "adt.user",
  pendingEmail: "adt.pendingEmail",
};

// colors for error buckets. charts + pills both read from here.
export const ERROR_COLORS = {
  off_by_one: "#f59e0b",
  logic: "#ef4444",
  time_complexity_issue: "#6366f1",
  base_case_issue: "#10b981",
  null_handling: "#64748b",
  unknown: "#94a3b8",
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
