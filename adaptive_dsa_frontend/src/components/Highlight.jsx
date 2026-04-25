import { Award, Trophy, Sparkles } from "lucide-react";
import { relativeTime } from "@/utils/formatters";

const ICONS = {
  hardest:     { icon: Trophy,   tone: "bg-amber-50 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300" },
  achievement: { icon: Sparkles, tone: "bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-300" },
  levelup:     { icon: Award,    tone: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-300" },
};

export default function Highlight({ item }) {
  const { icon: Icon, tone } = ICONS[item.type] || ICONS.achievement;
  return (
    <div className="flex items-center gap-3 py-3">
      <div className={`h-10 w-10 rounded-xl grid place-items-center ${tone}`}>
        <Icon className="h-5 w-5" strokeWidth={2} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{item.title}</div>
        <div className="text-xs text-slate-500 dark:text-slate-400">{item.meta}</div>
      </div>
      <div className="text-xs text-slate-400 dark:text-slate-500 shrink-0">{relativeTime(item.when)}</div>
    </div>
  );
}
