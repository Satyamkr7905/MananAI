/**
 * Mock API — returns realistic dummy data so the UI is fully usable with no
 * backend running. Real HTTP calls in `api.js` fall back to these on error or
 * when NEXT_PUBLIC_USE_MOCK_API is truthy.
 *
 * Each function returns a Promise to mirror the real network surface.
 */

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// ----------------------------- auth ---------------------------------------

export const mockSendOtp = async ({ email }) => {
  await delay(350);
  if (!email || !email.includes("@")) {
    const err = new Error("Please enter a valid email address.");
    err.status = 400;
    throw err;
  }
  return { ok: true, message: "OTP sent. (Demo OTP: 123456)", email };
};

export const mockVerifyOtp = async ({ email, otp }) => {
  await delay(400);
  if (otp !== "123456") {
    const err = new Error("Invalid OTP. (In demo mode, the OTP is 123456.)");
    err.status = 401;
    throw err;
  }
  return {
    token: "demo.jwt." + Math.random().toString(36).slice(2),
    user: {
      id: "u_" + email.slice(0, 3),
      email,
      name: email.split("@")[0].replace(/\W/g, " "),
      joinedAt: new Date().toISOString(),
    },
  };
};

// ------------------------------ stats -------------------------------------

const seedTopicProgress = () => [
  { topic: "arrays",  display: "Arrays",            level: 3, progress: 0.68, solved: 21, accuracy: 0.82 },
  { topic: "dp",      display: "Dynamic Programming", level: 2, progress: 0.42, solved: 11, accuracy: 0.55 },
  { topic: "graphs",  display: "Graphs",            level: 1, progress: 0.12, solved: 3,  accuracy: 0.40 },
  { topic: "trees",   display: "Trees",             level: 2, progress: 0.51, solved: 7,  accuracy: 0.62 },
  { topic: "strings", display: "Strings",           level: 2, progress: 0.35, solved: 4,  accuracy: 0.58 },
];

const seedProgressSeries = () => {
  // Fabricate a believable 14-day curve that trends upward with noise.
  const out = [];
  const today = new Date();
  let level = 1.6;
  let acc = 0.52;
  for (let i = 13; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    level = Math.min(5, level + 0.05 + Math.random() * 0.12 - 0.04);
    acc = Math.max(0.2, Math.min(0.98, acc + (Math.random() - 0.4) * 0.06));
    out.push({
      date: d.toISOString().slice(0, 10),
      label: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      level: +level.toFixed(2),
      accuracy: +acc.toFixed(2),
    });
  }
  return out;
};

export const mockGetStats = async () => {
  await delay(250);
  const topics = seedTopicProgress();
  const strongest = topics.reduce((a, b) => (b.progress > a.progress ? b : a));
  const weakest   = topics.reduce((a, b) => (b.progress < a.progress ? b : a));
  return {
    streak: 7,
    totalSolved: 46,
    accuracy: 0.78,
    level: 3,
    topics,
    strongest,
    weakest,
    progressSeries: seedProgressSeries(),
    highlights: [
      { id: "h1", type: "hardest",     title: "Edit Distance",         meta: "DP · difficulty 5",  when: new Date(Date.now() - 86400000 * 2).toISOString() },
      { id: "h2", type: "achievement", title: "7-day streak",          meta: "Keep it going!",     when: new Date().toISOString() },
      { id: "h3", type: "levelup",     title: "Arrays leveled to 3",   meta: "Unlocks harder set", when: new Date(Date.now() - 86400000 * 1).toISOString() },
    ],
  };
};

// ---------------------------- questions -----------------------------------

/**
 * Mock question bank. Each question is rich enough to drive the UI:
 *   - id, topic, title, difficulty (1-5)
 *   - description, tags, time_budget_seconds
 *   - reason: pre-computed "why this question" text (in prod the backend
 *     would generate this contextually from the learner's state)
 */
const QUESTIONS = [
  // ---------- arrays ----------
  { id: "arr_001", topic: "arrays", title: "Sum of Array", difficulty: 1,
    description: "Given an integer array nums, return the sum of all elements.",
    reason: "warming up with fundamentals — a confidence builder at difficulty 1/5.",
    tags: ["loop", "accumulator"], time_budget_seconds: 60 },
  { id: "arr_002", topic: "arrays", title: "Find Maximum", difficulty: 1,
    description: "Return the largest value in a non-empty array nums.",
    reason: "quick win on a common pattern (running tracker) at difficulty 1/5.",
    tags: ["loop", "tracking"], time_budget_seconds: 60 },
  { id: "arr_003", topic: "arrays", title: "Reverse In-Place", difficulty: 2,
    description: "Reverse an array in-place using O(1) extra space.",
    reason: "introduces the two-pointer pattern; watch for off-by-one in your loop bounds.",
    tags: ["two_pointer", "off_by_one"], time_budget_seconds: 120 },
  { id: "arr_004", topic: "arrays", title: "Remove Duplicates (Sorted)", difficulty: 2,
    description: "Given a sorted array, remove duplicates in-place and return the new length.",
    reason: "slow/fast pointer practice — reinforces last session's two-pointer work.",
    tags: ["two_pointer", "off_by_one"], time_budget_seconds: 180 },
  { id: "arr_005", topic: "arrays", title: "Two Sum", difficulty: 3,
    description: "Given an integer array nums and an integer target, return the indices of the two numbers such that they add up to target. You may assume exactly one solution exists.",
    reason: "targets your weak spot (hash_map); sits in your learning zone (~75% predicted success, difficulty 3/5).",
    tags: ["hash_map", "index"], time_budget_seconds: 240 },
  { id: "arr_006", topic: "arrays", title: "Maximum Subarray Sum", difficulty: 3,
    description: "Find the contiguous subarray with the largest sum (Kadane's algorithm).",
    reason: "bridges arrays and DP thinking — useful before your upcoming DP questions.",
    tags: ["kadane", "running_sum"], time_budget_seconds: 300 },
  { id: "arr_007", topic: "arrays", title: "Longest Substring Without Repeating Characters", difficulty: 4,
    description: "Given a string, find the length of the longest substring with all unique characters.",
    reason: "sliding window + hash set — a deliberate stretch at difficulty 4/5 to grow your ceiling.",
    tags: ["sliding_window", "hash_map"], time_budget_seconds: 360 },
  { id: "arr_008", topic: "arrays", title: "Trapping Rain Water", difficulty: 5,
    description: "Given heights representing an elevation map, compute how much water can be trapped.",
    reason: "hard two-pointer problem — attempt it with a clear invariant before optimizing.",
    tags: ["two_pointer", "hard"], time_budget_seconds: 600 },

  // ---------- dp ----------
  { id: "dp_001", topic: "dp", title: "Fibonacci Number", difficulty: 1,
    description: "Return the n-th Fibonacci number (F(0)=0, F(1)=1).",
    reason: "bottom-up DP fundamentals at difficulty 1/5 — a gentle start.",
    tags: ["base_case", "bottom_up"], time_budget_seconds: 90 },
  { id: "dp_002", topic: "dp", title: "Climbing Stairs", difficulty: 1,
    description: "You can climb 1 or 2 steps at a time. How many distinct ways to reach step n?",
    reason: "reinforces the dp[i] = dp[i-1] + dp[i-2] pattern at difficulty 1/5.",
    tags: ["base_case", "1d_dp"], time_budget_seconds: 120 },
  { id: "dp_003", topic: "dp", title: "House Robber", difficulty: 2,
    description: "You are a robber planning to rob houses along a street. You cannot rob two adjacent houses. Determine the maximum amount of money you can rob without alerting the police.",
    reason: "introduces the adjacent-choice DP pattern; a deliberate stretch at difficulty 2/5.",
    tags: ["1d_dp", "state_definition"], time_budget_seconds: 240 },
  { id: "dp_004", topic: "dp", title: "Min Cost Climbing Stairs", difficulty: 2,
    description: "Pay cost[i] to step on stair i; move 1 or 2 steps. Minimum cost to reach the top.",
    reason: "careful base-case setup — you've slipped on base_case_issue before, worth practicing.",
    tags: ["1d_dp", "base_case"], time_budget_seconds: 240 },
  { id: "dp_005", topic: "dp", title: "Coin Change", difficulty: 3,
    description: "Given coins and amount, return the fewest coins needed to make amount, or -1 if impossible.",
    reason: "unbounded-knapsack flavor at difficulty 3/5 — nails down state-definition discipline.",
    tags: ["1d_dp", "state_definition"], time_budget_seconds: 420 },
  { id: "dp_006", topic: "dp", title: "Longest Increasing Subsequence", difficulty: 3,
    description: "Return the length of the longest strictly increasing subsequence of nums.",
    reason: "start with O(n^2) DP; the O(n log n) variant is a stretch goal.",
    tags: ["1d_dp"], time_budget_seconds: 480 },
  { id: "dp_007", topic: "dp", title: "0/1 Knapsack", difficulty: 4,
    description: "Pick items (each at most once) with weights and values to maximize value under capacity W.",
    reason: "canonical 2D DP — a deliberate ceiling-raiser at difficulty 4/5.",
    tags: ["2d_dp", "knapsack"], time_budget_seconds: 540 },
  { id: "dp_008", topic: "dp", title: "Edit Distance", difficulty: 5,
    description: "Compute the minimum number of insert/delete/replace operations to convert word1 to word2.",
    reason: "hard 2D DP with careful base cases — take it slow.",
    tags: ["2d_dp", "base_case", "hard"], time_budget_seconds: 720 },

  // ---------- graphs ----------
  { id: "g_001", topic: "graphs", title: "Depth-First Traversal", difficulty: 1,
    description: "Given an adjacency list and a start node, print nodes in DFS order.",
    reason: "graph basics — recursive traversal pattern you'll reuse constantly.",
    tags: ["dfs", "recursion"], time_budget_seconds: 180 },
  { id: "g_002", topic: "graphs", title: "Number of Islands", difficulty: 3,
    description: "Given a 2D grid of '1' (land) and '0' (water), count the number of islands.",
    reason: "grid DFS/BFS — very common interview pattern at difficulty 3/5.",
    tags: ["dfs", "bfs", "grid"], time_budget_seconds: 360 },
  { id: "g_003", topic: "graphs", title: "Course Schedule", difficulty: 4,
    description: "Given prerequisites, determine whether you can finish all courses (cycle detection).",
    reason: "topological-order thinking — a stretch at difficulty 4/5.",
    tags: ["topological_sort", "cycle_detection"], time_budget_seconds: 480 },

  // ---------- trees ----------
  { id: "t_001", topic: "trees", title: "Maximum Depth of Binary Tree", difficulty: 1,
    description: "Given a binary tree's root, return its maximum depth.",
    reason: "tree recursion warm-up — clear base case, one recursive step.",
    tags: ["recursion", "base_case"], time_budget_seconds: 120 },
  { id: "t_002", topic: "trees", title: "Invert Binary Tree", difficulty: 2,
    description: "Invert a binary tree: swap left and right children at every node.",
    reason: "classic recursive transformation at difficulty 2/5.",
    tags: ["recursion"], time_budget_seconds: 180 },
  { id: "t_003", topic: "trees", title: "Validate BST", difficulty: 3,
    description: "Determine if a binary tree is a valid Binary Search Tree.",
    reason: "requires careful invariant tracking — builds state-definition discipline.",
    tags: ["recursion", "state_definition"], time_budget_seconds: 300 },
];

// Stable-ish rotation pointer; real backends would rank by your state instead.
let QUESTION_INDEX = 0;

/**
 * Pick the next question honoring optional topic/difficulty filters and an
 * exclusion list (the caller's "already mastered, don't repeat" set).
 */
export const mockGetNextQuestion = async ({ topic, difficulty, excludeIds = [] } = {}) => {
  await delay(180);

  let pool = QUESTIONS.filter((q) => !excludeIds.includes(q.id));
  if (topic && topic !== "all")         pool = pool.filter((q) => q.topic === topic);
  if (difficulty && difficulty !== "all") pool = pool.filter((q) => q.difficulty === Number(difficulty));

  if (pool.length === 0) return null; // UI shows an "all mastered" empty state

  const q = pool[QUESTION_INDEX % pool.length];
  QUESTION_INDEX += 1;
  return q;
};

/** Full list of topics, for the filter picker. */
export const mockGetTopics = async () => {
  await delay(80);
  const byKey = {};
  for (const q of QUESTIONS) {
    byKey[q.topic] = (byKey[q.topic] || 0) + 1;
  }
  return Object.entries(byKey).map(([key, count]) => ({
    key,
    label: { arrays: "Arrays", dp: "Dynamic Programming", graphs: "Graphs", trees: "Trees", strings: "Strings" }[key] || key,
    count,
  }));
};

// ---------------------------- submit --------------------------------------

export const mockSubmitAnswer = async ({ questionId, answer, hintsUsed = 0 }) => {
  await delay(420);
  const text = (answer || "").toLowerCase();
  const bruteForce = /brute|nested\s*for|o\(n\^?2\)/.test(text);
  const hashMapHit = /hash|map|dictionary|complement/.test(text);
  const dpHit = /dp\[|recurrence|i-1|i-2|base case/.test(text);

  let score = 0;
  if (hashMapHit) score = Math.max(score, 0.85);
  if (dpHit) score = Math.max(score, 0.75);
  if (bruteForce && score < 0.4) score = 0.35;
  if (!score && text.length > 20) score = 0.25;

  const correct = score >= 0.65;
  return {
    correct,
    score,
    error_type: correct ? null : bruteForce ? "time_complexity_issue" : "logic",
    matched: [hashMapHit && "hash", hashMapHit && "complement", dpHit && "dp"].filter(Boolean),
    missed: correct ? [] : ["edge case", "invariant"].slice(0, 2),
    notes: correct
      ? "Great — your approach hits the target complexity."
      : "You're on the right track; tighten the invariant.",
    questionId,
  };
};

// ---------------------------- hints ---------------------------------------

const HINT_TEXT = {
  1: "Start by naming the pattern family. What kind of problem is this — scan, two-pointer, hashmap, DP? Write down the invariant in one sentence before coding.",
  2: "Think about the data structure that gives you O(1) lookups. As you scan, can you store something now that you'd want to look up later? Try naming the exact invariant each iteration preserves.",
  3: "Here's the full approach (still implement it yourself):\n  1. Iterate once through the array, index i.\n  2. For each element, check if the required complement is already in your hash map.\n  3. If yes, return the stored index and i.\n  4. Otherwise, record the current element -> index and continue.\n  5. This runs in O(n) time and O(n) space.",
};

export const mockGetHint = async ({ level = 1 }) => {
  await delay(320);
  return { level, text: HINT_TEXT[Math.min(3, Math.max(1, level))] };
};

// ---------------------------- analytics -----------------------------------

export const mockGetAnalytics = async () => {
  await delay(260);
  return {
    mistakeBreakdown: [
      { key: "off_by_one",            count: 8 },
      { key: "logic",                 count: 6 },
      { key: "time_complexity_issue", count: 5 },
      { key: "base_case_issue",       count: 3 },
      { key: "null_handling",         count: 2 },
    ],
    weekly: [
      { day: "Mon", solved: 4, accuracy: 0.60 },
      { day: "Tue", solved: 5, accuracy: 0.68 },
      { day: "Wed", solved: 3, accuracy: 0.72 },
      { day: "Thu", solved: 7, accuracy: 0.74 },
      { day: "Fri", solved: 6, accuracy: 0.80 },
      { day: "Sat", solved: 8, accuracy: 0.82 },
      { day: "Sun", solved: 5, accuracy: 0.78 },
    ],
    accuracyTrend: seedProgressSeries().map((p) => ({ label: p.label, accuracy: p.accuracy })),
  };
};
