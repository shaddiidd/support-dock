export function cn(...values) {
  return values.filter(Boolean).join(" ");
}

export function Eyebrow({ children, className }) {
  return (
    <p
      className={cn(
        "mb-3 text-xs font-bold uppercase tracking-[0.14em]",
        className
      )}
    >
      {children}
    </p>
  );
}

export function Field({ label, hint, as = "input", className, ...props }) {
  const Control = as;
  return (
    <label className="grid gap-1.5 text-sm font-semibold">
      {label}
      <Control
        className={cn(
          "w-full resize-y rounded-xl border border-line bg-surface px-3.5 py-3 text-ink outline-none focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-harbor",
          className
        )}
        {...props}
      />
      {hint ? <span className="text-xs font-medium text-muted">{hint}</span> : null}
    </label>
  );
}

export function Button({ variant = "primary", className, ...props }) {
  const variants = {
    primary:
      "bg-harbor font-bold text-white hover:bg-harbor-deep disabled:cursor-wait disabled:opacity-70",
    ghost:
      "border border-paper/30 bg-transparent text-paper hover:bg-paper/10",
    quiet:
      "border border-line bg-transparent font-semibold text-ink hover:bg-paper",
    danger:
      "border border-red-800 bg-transparent font-bold text-red-800 hover:bg-red-50",
    dashed:
      "w-full border border-dashed border-paper/30 bg-transparent font-bold text-paper hover:bg-paper/10",
    text: "bg-transparent text-paper/80 hover:text-paper",
  };

  return (
    <button
      className={cn("rounded-xl px-4 py-3", variants[variant], className)}
      {...props}
    />
  );
}

export function Alert({ tone = "error", children }) {
  const tones = {
    error: "bg-red-50 text-red-800",
    success: "bg-emerald-50 text-emerald-800",
    warning: "bg-amber-50 text-amber-900",
  };

  return (
    <p className={cn("rounded-xl px-3.5 py-3 text-sm", tones[tone])} role="alert">
      {children}
    </p>
  );
}

export function Panel({ children, className }) {
  return (
    <section
      className={cn(
        "w-full max-w-xl rounded-[18px] border border-line bg-surface p-5 shadow-card sm:p-8",
        className
      )}
    >
      {children}
    </section>
  );
}

export function BootScreen({ children }) {
  return (
    <div className="grid min-h-screen place-items-center text-muted" role="status">
      <div className="grid justify-items-center gap-3">
        <img src="/logo.png" alt="" className="h-12 w-12 rounded-2xl object-cover" />
        <p>{children}</p>
      </div>
    </div>
  );
}
