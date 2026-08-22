import { ArrowRight, Award, CheckCircle2, Clock3, Route } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { api } from "../services/http";
import type { LearningPath } from "../types/api";

export default function LearningPathsPage() {
  const query = useQuery({
    queryKey: ["employee-learning-paths"],
    queryFn: () => api<LearningPath[]>("/employee/learning-paths"),
  });
  if (query.isLoading) return <LoadingState label="Montando suas trilhas…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="section-kicker">Aprendizagem guiada</span>
          <h1>Minhas trilhas</h1>
          <p>Avance na ordem recomendada e acompanhe sua evolução.</p>
        </div>
      </div>
      {query.data.length === 0 ? (
        <div className="empty-hero">
          <Route />
          <h2>Nenhuma trilha atribuída.</h2>
          <p>Quando uma jornada for liberada para você, ela aparecerá aqui.</p>
        </div>
      ) : (
        <div className="path-card-grid">
          {query.data.map((path) => (
            <Link className="path-card" to={`/app/paths/${path.id}`} key={path.id}>
              <div className="path-card-icon">{path.completed ? <Award /> : <Route />}</div>
              <span className="section-kicker">{path.items.length} etapas</span>
              <h2>{path.title}</h2>
              <p>{path.description}</p>
              <div className="path-progress">
                <span>
                  <i style={{ width: `${path.progress_percent ?? 0}%` }} />
                </span>
                <strong>{path.progress_percent ?? 0}%</strong>
              </div>
              <footer>
                <span>
                  {path.completed ? <CheckCircle2 size={14} /> : <Clock3 size={14} />}
                  {path.completed
                    ? "Concluída"
                    : path.due_date
                      ? `Prazo ${formatDate(path.due_date)}`
                      : "No seu ritmo"}
                </span>
                <ArrowRight size={16} />
              </footer>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}
