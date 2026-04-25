import { Inbox } from "lucide-react";
import { cn } from "@/utils/cn";

export default function EmptyState({ title = "Nothing here yet", description, icon: Icon = Inbox, action, className }) {
  return (
    <div className={cn("card p-10 text-center flex flex-col items-center", className)}>
      <div className="h-12 w-12 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center">
        <Icon className="h-6 w-6" strokeWidth={1.75} />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-slate-500 max-w-md">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
