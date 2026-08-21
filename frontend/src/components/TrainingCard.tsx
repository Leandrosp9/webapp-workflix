import { ArrowUpRight, Check, Clock3, FileText, Play } from "lucide-react";
import { Link } from "react-router-dom";

import type { Training } from "../types/api";

interface TrainingCardProps {
  training: Training;
  admin?: boolean;
}

export function TrainingCard({ training, admin = false }: TrainingCardProps) {
  const progress = training.progress_percent ?? 0;
  const target = admin ? `/admin/trainings/${training.id}` : `/app/training/${training.id}`;
  return (
    <Link className="training-card" to={target}>
      <div
        className="training-art"
        style={
          training.thumbnail_url
            ? {
                backgroundImage: `linear-gradient(180deg, transparent, rgba(3,6,12,.78)), url(${training.thumbnail_url})`,
              }
            : undefined
        }
      >
        <span className={`type-chip type-${training.type.toLowerCase()}`}>
          {training.type === "VIDEO" ? <Play size={11} /> : <FileText size={11} />}
          {training.type}
        </span>
        {progress === 100 && (
          <span className="complete-chip">
            <Check size={12} /> concluído
          </span>
        )}
      </div>
      <div className="training-card-body">
        <div className="training-card-meta">
          <span>
            <Clock3 size={13} /> {training.estimated_minutes} min
          </span>
          {admin && (
            <span className={`status-${training.status.toLowerCase()}`}>{training.status}</span>
          )}
        </div>
        <h3>{training.title}</h3>
        <p>{training.description}</p>
        {!admin && (
          <div className="card-progress">
            <div>
              <span style={{ width: `${progress}%` }} />
            </div>
            <small>{progress}%</small>
          </div>
        )}
        <span className="card-open">
          {admin ? "Editar conteúdo" : progress ? "Continuar" : "Começar"}{" "}
          <ArrowUpRight size={15} />
        </span>
      </div>
    </Link>
  );
}
