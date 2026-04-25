import { cn } from "@/utils/cn";

export default function Loader({ label = "", className, size = "md" }) {
  const dot = size === "sm" ? "h-1.5 w-1.5" : "h-2.5 w-2.5";
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex items-center gap-1.5">
        <span className={cn(dot, "rounded-full bg-brand-500 animate-pulse-dot")} />
        <span className={cn(dot, "rounded-full bg-brand-500 animate-pulse-dot [animation-delay:200ms]")} />
        <span className={cn(dot, "rounded-full bg-brand-500 animate-pulse-dot [animation-delay:400ms]")} />
      </div>
      {label && <span className="text-sm text-slate-500">{label}</span>}
    </div>
  );
}
