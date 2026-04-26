// NovaMascot — the floating Nova bot that reacts to user events.
//
// Moods:
//   neutral  — gentle idle bob; wanders to random "park spots" every few seconds
//   happy    — little hop + sparkle, after a partial/correct answer
//   excited  — dances with a party popper, after a confident-correct answer
//   sad      — slow droop + tear, after a wrong answer
//   thinking — idle bob + thought bubble, while hints/requests are in flight
//
// The bot lives fixed at the bottom-right and slides around using CSS
// transforms. Double-click to hide for the session. Re-mount or clear
// sessionStorage key "novaHidden" to bring it back.

import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { useMascot } from "@/context/MascotContext";

const BOT_W = 96;
const BOT_H = 140;
const EDGE_MARGIN = 24;
const TOP_SAFE = 80;
const BOTTOM_SAFE = 24;

const MOOD_CONFIG = {
  neutral: {
    emoji: "",
    animation: "novaBob 3.2s ease-in-out infinite",
    filter: "drop-shadow(0 8px 20px rgba(68, 79, 45, .25))",
    fallbackMessage: "",
  },
  happy: {
    emoji: "✨",
    animation: "novaHop 0.55s ease-in-out infinite",
    filter: "drop-shadow(0 0 16px rgba(134,148,99,.45))",
    fallbackMessage: "Nice one!",
  },
  excited: {
    emoji: "🎉",
    animation: "novaDance 0.7s ease-in-out infinite",
    filter: "drop-shadow(0 0 22px rgba(255, 205, 77, .55))",
    fallbackMessage: "You crushed it!",
  },
  sad: {
    emoji: "💧",
    animation: "novaDroop 1.8s ease-in-out infinite",
    filter: "grayscale(.35) brightness(.85) drop-shadow(0 6px 14px rgba(0,0,0,.25))",
    fallbackMessage: "Oof — we'll get the next one.",
  },
  thinking: {
    emoji: "💭",
    animation: "novaBob 2.4s ease-in-out infinite",
    filter: "drop-shadow(0 6px 16px rgba(15,23,42,.25))",
    fallbackMessage: "Hmm… thinking.",
  },
};

// Returns an absolute {x, y} somewhere inside the viewport, avoiding the
// navbar strip at the top and a small safety margin on all edges.
function randomSpot() {
  if (typeof window === "undefined") return { x: EDGE_MARGIN, y: TOP_SAFE };
  const maxX = Math.max(EDGE_MARGIN, window.innerWidth - BOT_W - EDGE_MARGIN);
  const maxY = Math.max(TOP_SAFE + 1, window.innerHeight - BOT_H - BOTTOM_SAFE);
  const x = Math.floor(EDGE_MARGIN + Math.random() * Math.max(1, maxX - EDGE_MARGIN));
  const y = Math.floor(TOP_SAFE + Math.random() * Math.max(1, maxY - TOP_SAFE));
  return { x, y };
}

function cornerSpot() {
  // Bottom-right spotlight used when Nova reacts to an event.
  if (typeof window === "undefined") return { x: EDGE_MARGIN, y: TOP_SAFE };
  return {
    x: Math.max(EDGE_MARGIN, window.innerWidth - BOT_W - EDGE_MARGIN),
    y: Math.max(TOP_SAFE, window.innerHeight - BOT_H - BOTTOM_SAFE),
  };
}

export default function NovaMascot() {
  const { mood, message } = useMascot();
  const [pos, setPos] = useState({ x: EDGE_MARGIN, y: TOP_SAFE });
  const [hidden, setHidden] = useState(false);
  const wanderRef = useRef(null);

  // Initial spot + keep mascot on-screen when the viewport resizes.
  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    setPos(cornerSpot());
    const onResize = () => {
      setPos((p) => ({
        x: Math.min(p.x, Math.max(EDGE_MARGIN, window.innerWidth - BOT_W - EDGE_MARGIN)),
        y: Math.min(p.y, Math.max(TOP_SAFE, window.innerHeight - BOT_H - BOTTOM_SAFE)),
      }));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Restore dismiss-per-session.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (sessionStorage.getItem("novaHidden") === "1") setHidden(true);
  }, []);

  const snapToCorner = useCallback(() => setPos(cornerSpot()), []);

  // Idle wander: only while neutral/thinking. Nova drifts to a fresh random
  // point anywhere in the viewport. The interval (4.5s) is tuned to be
  // slightly shorter than the CSS transition (5s) so Nova is almost always
  // gliding — never teleporting, never sitting perfectly still for long.
  useEffect(() => {
    if (mood !== "neutral" && mood !== "thinking") {
      snapToCorner();
      return undefined;
    }
    // Kick off a move immediately so Nova doesn't idle for 4.5s on mount.
    setPos(randomSpot());
    wanderRef.current = setInterval(() => {
      setPos(randomSpot());
    }, 4500);
    return () => clearInterval(wanderRef.current);
  }, [mood, snapToCorner]);

  if (hidden) return null;

  const cfg = MOOD_CONFIG[mood] || MOOD_CONFIG.neutral;
  const bubble = message || cfg.fallbackMessage;

  const dismiss = () => {
    setHidden(true);
    if (typeof window !== "undefined") sessionStorage.setItem("novaHidden", "1");
  };

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed top-0 left-0 z-[60] select-none"
      style={{
        // translate3d forces GPU compositing so the glide stays at 60fps
        // even when the main thread is busy rendering charts/tables.
        transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
        transition: "transform 5s cubic-bezier(.45, 0, .35, 1)",
        willChange: "transform",
        backfaceVisibility: "hidden",
      }}
    >
      {bubble && (
        <div
          className="pointer-events-none absolute -top-12 right-0 max-w-[220px] px-3 py-1.5 rounded-2xl text-[11px] font-medium
                     bg-white/95 text-slate-800 shadow-soft ring-1 ring-slate-200
                     dark:bg-slate-800/95 dark:text-slate-100 dark:ring-slate-700
                     animate-fade-in"
        >
          {bubble}
          <span
            className="absolute -bottom-1 right-6 h-2 w-2 rotate-45
                       bg-white/95 ring-1 ring-slate-200
                       dark:bg-slate-800/95 dark:ring-slate-700"
            aria-hidden
          />
        </div>
      )}

      <div
        className="relative pointer-events-auto group"
        title="Double-click to hide"
        style={{ width: BOT_W, height: BOT_H }}
      >
        {cfg.emoji && (
          <div className="absolute -top-3 -left-3 text-2xl animate-fade-in drop-shadow-sm">
            {cfg.emoji}
          </div>
        )}

        <button
          type="button"
          onClick={dismiss}
          className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-slate-900/70 text-white
                     opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center
                     ring-1 ring-black/10 z-10"
          aria-label="Hide Nova"
        >
          <X className="h-3 w-3" />
        </button>

        <img
          src="/nova-bot.png"
          alt="Nova"
          draggable={false}
          onDoubleClick={dismiss}
          style={{
            width: BOT_W,
            height: BOT_H,
            objectFit: "contain",
            animation: cfg.animation,
            filter: cfg.filter,
            transformOrigin: "50% 85%",
          }}
        />
      </div>
    </div>
  );
}
