import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import ProtectedRoute from "./ProtectedRoute";
import NovaMascot from "./NovaMascot";
import { useMascot } from "@/context/MascotContext";

/**
 * AppLayout — the chrome shared by every authenticated page.
 *
 * Wraps children in ProtectedRoute so pages never have to think about auth.
 * Page components render only the *content* of the main column.
 */
export default function AppLayout({ children, title, subtitle, actions }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const router = useRouter();
  const { setMood, clearMood } = useMascot();

  // Nova gives a friendly nod whenever the user lands on a new page. The
  // greeting is short (2.5s) so it's never in the way.
  useEffect(() => {
    const greetings = {
      "/dashboard": "Welcome back!",
      "/practice":  "Let's practice!",
      "/interview": "Interview mode — good luck!",
      "/history":   "Here's your progress.",
      "/analytics": "Let's review.",
    };
    const msg = greetings[router.pathname] || "";
    if (msg) setMood("happy", msg, 2500);
    else clearMood();
  }, [router.pathname, setMood, clearMood]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen flex flex-col bg-cream-50 dark:bg-slate-950">
        <Navbar onMenuClick={() => setMobileMenuOpen(true)} />
        <div className="flex-1 flex">
          <Sidebar open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
          <main className="flex-1 min-w-0">
            <div className="mx-auto w-full max-w-7xl px-4 md:px-8 py-8">
              {(title || actions) && (
                <div className="mb-8 flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    {title && <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 tracking-tight">{title}</h1>}
                    {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
                  </div>
                  {actions && <div className="flex items-center gap-2">{actions}</div>}
                </div>
              )}
              {children}
            </div>
          </main>
        </div>
        <NovaMascot />
      </div>
    </ProtectedRoute>
  );
}
