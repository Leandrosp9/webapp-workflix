interface BrandProps {
  compact?: boolean;
  splash?: boolean;
}

export function Brand({ compact = false, splash = false }: BrandProps) {
  return (
    <div
      className={`brand ${compact ? "brand-compact" : ""} ${splash ? "brand-splash" : ""}`.trim()}
      aria-label="Workflix"
    >
      <span className="brand-logo" aria-hidden="true">
        <img src="/brand/workflix-logo.png" alt="" />
      </span>
    </div>
  );
}
