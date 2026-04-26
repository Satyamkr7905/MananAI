// MascotContext — global mood state for the Nova mascot.
//
// Any component can call `setMood("excited" | "happy" | "sad" | "thinking" |
// "neutral", messageOverride?, durationMs?)`. Temporary moods auto-revert
// to neutral after a sensible default duration so the mascot never gets
// stuck in a loud state.

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const MOOD_DURATIONS_MS = {
  neutral: 0,
  excited: 5000,
  happy: 3500,
  sad: 5000,
  thinking: 4000,
};

const MascotContext = createContext({
  mood: "neutral",
  message: "",
  setMood: () => {},
  clearMood: () => {},
});

export function MascotProvider({ children }) {
  const [mood, setMoodState] = useState("neutral");
  const [message, setMessage] = useState("");
  const timerRef = useRef(null);

  const clearMood = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setMoodState("neutral");
    setMessage("");
  }, []);

  const setMood = useCallback((nextMood, nextMessage = "", ms) => {
    const m = nextMood || "neutral";
    setMoodState(m);
    setMessage(nextMessage || "");
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const duration = typeof ms === "number" ? ms : MOOD_DURATIONS_MS[m] ?? 0;
    if (duration > 0) {
      timerRef.current = setTimeout(() => {
        setMoodState("neutral");
        setMessage("");
        timerRef.current = null;
      }, duration);
    }
  }, []);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  return (
    <MascotContext.Provider value={{ mood, message, setMood, clearMood }}>
      {children}
    </MascotContext.Provider>
  );
}

export const useMascot = () => useContext(MascotContext);
