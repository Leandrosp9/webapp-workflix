import { Brand } from "./Brand";

export function AppLoadingScreen({ label = "Preparando seu espaço…" }: { label?: string }) {
  return (
    <main className="route-fallback" aria-busy="true" aria-label="Carregando Workflix">
      <div className="route-loading-brand">
        <span className="route-loading-orbit" aria-hidden="true" />
        <Brand splash />
      </div>
      <strong>{label}</strong>
      <span className="route-loading-bar" aria-hidden="true">
        <i />
      </span>
    </main>
  );
}
