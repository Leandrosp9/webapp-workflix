interface BrandProps {
  compact?: boolean;
}

export function Brand({ compact = false }: BrandProps) {
  return (
    <div className={`brand ${compact ? "brand-compact" : ""}`} aria-label="Workflix">
      <span className="brand-logo" aria-hidden="true">
        <img src="/brand/workflix-logo.png" alt="" />
      </span>
    </div>
  );
}
