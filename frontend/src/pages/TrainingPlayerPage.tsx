import { ArrowLeft, ArrowRight, CheckCircle2, Clock3, FileText, PlayCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { api, downloadPdf } from "../services/http";
import type { Training } from "../types/api";

export default function TrainingPlayerPage() {
  const { trainingId = "" } = useParams();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["training", trainingId],
    queryFn: () => api<Training>(`/employee/trainings/${trainingId}`),
  });
  const progress = useMutation({
    mutationFn: (percent: number) =>
      api<Training>(`/employee/trainings/${trainingId}/progress`, {
        method: "PATCH",
        body: JSON.stringify({ progress_percent: percent }),
      }),
    onSuccess: (training) => {
      queryClient.setQueryData(["training", trainingId], training);
      void queryClient.invalidateQueries({ queryKey: ["employee-home"] });
    },
  });

  if (query.isLoading) return <LoadingState label="Abrindo treinamento…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const training = query.data;
  const percent = training.progress_percent ?? 0;

  return (
    <div className="player-page">
      <Link className="back-link" to="/app">
        <ArrowLeft size={16} /> Voltar para início
      </Link>
      <div className="player-layout">
        <article className="player-content">
          <div className="player-heading">
            <span className={`type-chip type-${training.type.toLowerCase()}`}>{training.type}</span>
            <h1>{training.title}</h1>
            <p>{training.description}</p>
            <div>
              <span>
                <Clock3 size={14} /> {training.estimated_minutes} min
              </span>
              <span>{percent}% concluído</span>
            </div>
          </div>
          {training.type === "VIDEO" && training.video_url && (
            <div className="video-player">
              <PlayCircle size={58} />
              <a href={training.video_url} target="_blank" rel="noreferrer">
                Abrir vídeo em nova aba
              </a>
            </div>
          )}
          {training.type === "PDF" && training.has_pdf && (
            <div className="pdf-player">
              <FileText size={46} />
              <h2>Material em PDF</h2>
              <p>O documento é servido com autorização e não possui URL pública.</p>
              <button
                className="button secondary"
                type="button"
                onClick={() => void downloadPdf(training.id)}
              >
                Baixar material
              </button>
            </div>
          )}
          {training.content && <div className="article-content">{training.content}</div>}
        </article>
        <aside className="player-sidebar">
          <span className="section-kicker">Seu progresso</span>
          <strong>{percent}%</strong>
          <div className="large-progress">
            <span style={{ width: `${percent}%` }} />
          </div>
          <p>{percent === 100 ? "Treinamento concluído." : "Continue de onde parou."}</p>
          {training.has_quiz ? (
            <Link className="button primary" to={`/app/training/${training.id}/quiz`}>
              Fazer avaliação <ArrowRight size={16} />
            </Link>
          ) : (
            <button
              className="button primary"
              type="button"
              disabled={progress.isPending || percent === 100}
              onClick={() => progress.mutate(100)}
            >
              <CheckCircle2 size={16} /> {percent === 100 ? "Concluído" : "Marcar como concluído"}
            </button>
          )}
          {percent < 50 && (
            <button className="text-button" type="button" onClick={() => progress.mutate(50)}>
              Salvar progresso em 50%
            </button>
          )}
        </aside>
      </div>
    </div>
  );
}
