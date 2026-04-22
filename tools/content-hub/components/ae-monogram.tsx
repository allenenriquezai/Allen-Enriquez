import { cn } from "@/lib/utils";

export function AeMonogram({
  size = 36,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      aria-label="Allen Enriquez monogram"
    >
      <span
        className="ae-glow-text"
        style={{
          fontFamily: "var(--font-roboto-mono), ui-monospace, monospace",
          fontWeight: 700,
          fontStyle: "italic",
          fontSize: size * 0.58,
          letterSpacing: "-0.04em",
          color: "#02B3E9",
          lineHeight: 1,
        }}
      >
        AE
      </span>
    </div>
  );
}
