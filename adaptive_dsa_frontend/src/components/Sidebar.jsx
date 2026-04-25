import Link from "next/link";
import { useRouter } from "next/router";
import { BarChart3, GraduationCap, History, LayoutDashboard, X } from "lucide-react";
import { cn } from "@/utils/cn";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/practice",  label: "Practice",  icon: GraduationCap },
  { href: "/history",   label: "History",   icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

/**
 * Sidebar — persistent nav rail on md+; collapsible drawer on mobile.
 * The `open`/`onClose` props are only used in mobile drawer mode.
 */
export default function Sidebar({ open = false, onClose }) {
  const router = useRouter();

  const isActive = (href) =>
    router.pathname === href || router.pathname.startsWith(`${href}/`);

  const items = (
    <nav className="px-3 py-4 flex flex-col gap-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = isActive(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onClose}
            className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
              active
                ? "bg-brand-50 text-brand-700"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100",
            )}
          >
            <Icon className={cn("h-4.5 w-4.5", active ? "text-brand-600" : "text-slate-400 group-hover:text-slate-600")} />
            {label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <>
      {/* desktop rail */}
      <aside className="hidden md:flex md:flex-col md:w-60 md:shrink-0 md:border-r md:border-slate-200 md:bg-white">
        <div className="h-16 px-5 flex items-center border-b border-slate-200">
          <span className="section-title">Navigation</span>
        </div>
        {items}
        <div className="mt-auto p-4">
          <div className="rounded-xl bg-brand-50 ring-1 ring-brand-100 p-4">
            <div className="text-xs font-semibold text-brand-700">Adaptive mode</div>
            <p className="mt-1 text-[11px] leading-relaxed text-brand-700/80">
              The tutor picks questions in your learning zone and tracks every pattern.
            </p>
          </div>
        </div>
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="md:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-slate-900/50 animate-fade-in"
            onClick={onClose}
            aria-hidden
          />
          <div className="absolute left-0 top-0 bottom-0 w-72 bg-white shadow-xl animate-fade-in">
            <div className="h-16 px-5 flex items-center justify-between border-b border-slate-200">
              <span className="section-title">Navigation</span>
              <button onClick={onClose} className="btn-subtle !p-2" aria-label="Close menu">
                <X className="h-5 w-5" />
              </button>
            </div>
            {items}
          </div>
        </div>
      )}
    </>
  );
}
