import { Award, Check, ChevronLeft, Clock3, LockKeyhole, PlayCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { api } from "../services/http";
import type { LearningPath } from "../types/api";
import { trainingTypeLabel } from "../utils/labels";

export default function LearningPathDetailPage() {
  const { pathId } = useParams();
  const query = useQuery({
    queryKey: ["employee-learning-path", pathId],
    queryFn: () => api<LearningPath>(`/employee/learning-paths/${pathId}`),
    enabled: Boolean(pathId),
  });
  if (query.isLoading) return <LoadingState />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const path = query.data;
  return (
    <div className="path-detail-page">
      <Link className="back-link" to="/app/paths">
        <ChevronLeft size={15} /> Voltar às trilhas
      </Link>
      <header className="path-detail-hero">
        <div>
          <span className="section-kicker">Trilha de aprendizagem</span>
          <h1>{path.title}</h1>
          <p>{path.description}</p>
        </div>
        <div className="path-detail-score">
          {path.completed ? <Award /> : <strong>{path.progress_percent ?? 0}%</strong>}
          <span>{path.completed ? "Certificado emitido" : "progresso geral"}</span>
        </div>
      </header>
      <div className="path-step-list">
        {path.items.map((item, index) => {
          const completed = item.progress_percent === 100;
          const content = (
            <>
              <div className={`path-step-number ${completed ? "complete" : ""}`}>
                {completed ? <Check size={16} /> : index + 1}
              </div>
              <div className="path-step-copy">
                <span>
                  {item.required ? "Obrigatório" : "Complementar"} · {trainingTypeLabel(item.type)}
                </span>
                <h2>{item.title}</h2>
                <p>{item.description}</p>
              </div>
              <div className="path-step-meta">
                <span>
                  <Clock3 size={14} /> {item.estimated_minutes} min
                </span>
                {item.available ? <PlayCircle /> : <LockKeyhole />}
              </div>
            </>
          );
          return item.available ? (
            <Link className="path-step" to={`/app/training/${item.training_id}`} key={item.id}>
              {content}
            </Link>
          ) : (
            <div className="path-step locked" key={item.id}>
              {content}
            </div>
          );
        })}
      </div>
    </div>
  );
}
