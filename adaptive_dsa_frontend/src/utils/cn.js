import clsx from "clsx";

// thin clsx wrapper so components read nicely:
//   className={cn("btn", variant === "primary" && "btn-primary", className)}
export const cn = (...args) => clsx(...args);
