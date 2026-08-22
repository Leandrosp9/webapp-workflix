import { AlertTriangle, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Carregando…" }: { label?: string }) {
  return (
    <div className="page-state loading-state" aria-live="polite" aria-busy="true">
      <div className="skeleton-shell" aria-hidden="true">
        <span className="skeleton-line skeleton-kicker" />
        <span className="skeleton-line skeleton-title" />
        <span className="skeleton-line skeleton-copy" />
        <div className="skeleton-grid">
          <span />
          <span />
          <span />
        </div>
      </div>
      <p className="loading-label">{label}</p>
    </div>
  );
}

export function ErrorState({ retry }: { retry?: () => void }) {
  return (
    <div className="page-state error-state">
      <span className="state-icon" aria-hidden="true">
        <AlertTriangle />
      </span>
      <strong>Algo não saiu como esperado.</strong>
      <p>Confira se a API está disponível e tente novamente.</p>
      {retry && (
        <button className="button secondary" type="button" onClick={retry}>
          <RefreshCw size={15} /> Tentar novamente
        </button>
      )}
    </div>
  );
}
