import Link from "next/link";
import { Brain, LogOut, Menu, Moon, Sun } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/context/ThemeContext";

/**
 * Navbar — top bar with brand mark, theme toggle, user pill, and sign-out.
 *
 * Mobile: exposes a menu button that the parent layout wires up to toggle
 * the Sidebar. Desktop hides the button.
 */
export default function Navbar({ onMenuClick }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const initial = (user?.name || user?.email || "?").trim()[0]?.toUpperCase();

  return (
    <header className="sticky top-0 z-30 bg-white/85 dark:bg-slate-950/85 backdrop-blur ring-1 ring-slate-200/60 dark:ring-slate-800/80">
      <div className="h-16 px-4 md:px-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onMenuClick}
            className="md:hidden btn-subtle !p-2"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-brand-600 text-white grid place-items-center shadow-sm">
              <Brain className="h-4.5 w-4.5" strokeWidth={2.25} />
            </div>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              MANAN <span className="text-brand-600 dark:text-brand-400">AI</span>
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={toggleTheme}
            className="btn-subtle !p-2"
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title="Theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          {user && (
            <div className="hidden sm:flex items-center gap-2 pr-2">
              <div className="h-8 w-8 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-900/50 dark:text-brand-200 grid place-items-center text-sm font-semibold">
                {initial}
              </div>
              <div className="text-xs leading-tight">
                <div className="font-medium text-slate-900 dark:text-slate-100 capitalize">{user.name || user.email}</div>
                <div className="text-slate-500 dark:text-slate-400">{user.email}</div>
              </div>
            </div>
          )}
          <button onClick={logout} className="btn-ghost !py-2 !px-3 text-sm" aria-label="Sign out">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </div>
    </header>
  );
}
