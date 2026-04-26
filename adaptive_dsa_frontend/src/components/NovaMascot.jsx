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

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { useMascot } from "@/context/MascotContext";

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

// Translation offsets relative to the default bottom-right anchor. Nova
// shuffles between these to feel alive during idle moments.
const PARK_SPOTS = [
  { x: 0, y: 0 },
  { x: -220, y: -20 },
  { x: -520, y: 0 },
  { x: -120, y: -160 },
  { x: -380, y: -200 },
];

export default function NovaMascot() {
  const { mood, message } = useMascot();
  const [pos, setPos] = useState(PARK_SPOTS[0]);
  const [hidden, setHidden] = useState(false);
  const wanderRef = useRef(null);

  // Restore dismiss-per-session.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (sessionStorage.getItem("novaHidden") === "1") setHidden(true);
  }, []);

  // Idle wander: only while neutral/thinking so active moods stay spotlit.
  useEffect(() => {
    if (mood !== "neutral" && mood !== "thinking") {
      setPos(PARK_SPOTS[0]);
      return undefined;
    }
    wanderRef.current = setInterval(() => {
      const next = PARK_SPOTS[Math.floor(Math.random() * PARK_SPOTS.length)];
      setPos(next);
    }, 7500);
    return () => clearInterval(wanderRef.current);
  }, [mood]);

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
      className="pointer-events-none fixed bottom-4 right-4 z-[60] select-none"
      style={{
        transform: `translate(${pos.x}px, ${pos.y}px)`,
        transition: "transform 1.4s cubic-bezier(.22,1,.36,1)",
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

      <div className="relative pointer-events-auto group" title="Double-click to hide">
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
                     ring-1 ring-black/10"
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
            width: 96,
            height: 140,
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
