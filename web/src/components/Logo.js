import logo from "../assets/logo.png";

import { cn } from "./ui";

const sizes = {
  sm: "h-8 w-8 rounded-lg",
  md: "h-10 w-10 rounded-xl",
  lg: "h-16 w-16 rounded-2xl",
};

export function Logo({ size = "md", className }) {
  return (
    <img
      src={logo}
      alt=""
      className={cn("shrink-0 object-cover", sizes[size], className)}
    />
  );
}

export function BrandMark({ size = "md", kicker, inverted = false }) {
  return (
    <div className="flex items-center gap-3">
      <Logo size={size} />
      <div className="min-w-0">
        <p
          className={cn(
            "text-xs font-bold uppercase tracking-[0.14em]",
            inverted ? "text-paper" : "text-ink"
          )}
        >
          Support Dock
        </p>
        {kicker ? (
          <p className={cn("text-sm", inverted ? "text-paper/60" : "text-muted")}>
            {kicker}
          </p>
        ) : null}
      </div>
    </div>
  );
}
