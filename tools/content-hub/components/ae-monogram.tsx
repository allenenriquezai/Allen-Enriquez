import { cn } from "@/lib/utils";

export function AeMonogram({
  size = 36,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const radius = Math.round(size * 0.22);
  return (
    <div
      className={cn("relative inline-flex items-center justify-center shrink-0", className)}
      style={{
        width: size,
        height: size,
        background: "#06101a",
        border: "1.5px solid rgba(2,179,233,0.55)",
        borderRadius: radius,
        boxShadow: "0 0 10px rgba(2,179,233,0.18), inset 0 0 6px rgba(2,179,233,0.06)",
      }}
      aria-label="Allen Enriquez monogram"
    >
      <span
        style={{
          fontFamily: "var(--font-roboto-mono), ui-monospace, monospace",
          fontWeight: 700,
          fontStyle: "italic",
          fontSize: size * 0.44,
          letterSpacing: "-0.05em",
          color: "#02B3E9",
          lineHeight: 1,
          textShadow: "0 0 12px rgba(2,179,233,0.6)",
        }}
      >
        AE
      </span>
    </div>
  );
}
