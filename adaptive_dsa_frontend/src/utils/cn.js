import clsx from "clsx";

/**
 * Thin wrapper around clsx so components read nicely:
 *   className={cn("btn", variant === "primary" && "btn-primary", className)}
 */
export const cn = (...args) => clsx(...args);
