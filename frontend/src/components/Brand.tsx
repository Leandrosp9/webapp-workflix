interface BrandProps {
  compact?: boolean;
}

export function Brand({ compact = false }: BrandProps) {
  return (
    <div className="brand" aria-label="Workflix">
      <span className="brand-mark" aria-hidden="true">
        W
      </span>
      {!compact && <span className="brand-name">Workflix</span>}
    </div>
  );
}
