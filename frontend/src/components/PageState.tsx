import { LoaderCircle, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Carregando…" }: { label?: string }) {
  return (
    <div className="page-state" aria-live="polite">
      <LoaderCircle className="spin" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ retry }: { retry?: () => void }) {
  return (
    <div className="page-state error-state">
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
