import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  PlayCircle,
  Send,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { ApiError, api, downloadPdf } from "../services/http";
import type {
  DocumentVersion,
  EmployeeAcknowledgementStatus,
  RagAnswer,
  Training,
} from "../types/api";

export default function TrainingPlayerPage() {
  const { trainingId = "" } = useParams();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState("");
  const [ragError, setRagError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [downloadingPdf, setDownloadingPdf] = useState(false);
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
  const documentQuery = useQuery({
    queryKey: ["training-document", trainingId],
    queryFn: () => api<DocumentVersion>(`/trainings/${trainingId}/document`),
    enabled: Boolean(query.data?.has_pdf),
    retry: false,
    refetchInterval: (statusQuery) =>
      statusQuery.state.data &&
      ["UPLOADED", "EXTRACTING", "INDEXING"].includes(statusQuery.state.data.status)
        ? 2_000
        : false,
  });
  const acknowledgementQuery = useQuery({
    queryKey: ["training-acknowledgement", trainingId],
    queryFn: () =>
      api<EmployeeAcknowledgementStatus>(`/employee/trainings/${trainingId}/acknowledgement`),
    enabled: Boolean(query.data?.has_pdf),
    retry: false,
  });
  const acknowledgeDocument = useMutation({
    mutationFn: () =>
      api<EmployeeAcknowledgementStatus>(`/employee/trainings/${trainingId}/acknowledgement`, {
        method: "POST",
        body: JSON.stringify({
          document_version_id: acknowledgementQuery.data?.document_version_id,
        }),
      }),
    onSuccess: (status) => {
      queryClient.setQueryData(["training-acknowledgement", trainingId], status);
    },
  });
  const askDocument = useMutation({
    mutationFn: () =>
      api<RagAnswer>(`/trainings/${trainingId}/ask`, {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
    onMutate: () => setRagError(""),
    onError: (reason) =>
      setRagError(
        reason instanceof ApiError ? reason.message : "Não foi possível consultar o documento.",
      ),
  });

  async function handlePdfDownload() {
    setDownloadError("");
    setDownloadingPdf(true);
    try {
      await downloadPdf(trainingId);
    } catch (reason) {
      setDownloadError(
        reason instanceof ApiError ? reason.message : "Não foi possível baixar o material.",
      );
    } finally {
      setDownloadingPdf(false);
    }
  }

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
          {training.type === "VIDEO" && (
            <div className="video-player">
              <PlayCircle size={58} />
              <h2>Conteúdo em vídeo</h2>
              {training.video_url ? (
                <a href={training.video_url} target="_blank" rel="noreferrer">
                  Abrir vídeo em nova aba
                </a>
              ) : (
                <p>O material de apoio deste treinamento está disponível abaixo.</p>
              )}
            </div>
          )}
          {training.type === "PDF" && training.has_pdf && (
            <>
              <div className="pdf-player">
                <FileText size={46} />
                <h2>Material em PDF</h2>
                <p>O documento é servido com autorização e não possui URL pública.</p>
                <button
                  className="button secondary"
                  type="button"
                  disabled={downloadingPdf}
                  onClick={() => void handlePdfDownload()}
                >
                  {downloadingPdf ? "Preparando download…" : "Baixar material"}
                </button>
                {downloadError && <div className="form-error">{downloadError}</div>}
              </div>
              {acknowledgementQuery.data && (
                <section
                  className={`acknowledgement-panel ${
                    acknowledgementQuery.data.acknowledged ? "is-acknowledged" : ""
                  }`}
                >
                  <BadgeCheck size={25} />
                  <div>
                    <span className="section-kicker">Ciência do documento</span>
                    <h2>Versão {acknowledgementQuery.data.version_number}</h2>
                    <p>{acknowledgementQuery.data.attestation}</p>
                    {acknowledgementQuery.data.acknowledgement && (
                      <small>
                        Registrado em{" "}
                        {new Date(
                          acknowledgementQuery.data.acknowledgement.acknowledged_at,
                        ).toLocaleString("pt-BR")}
                        {" · SHA-256 "}
                        {acknowledgementQuery.data.document_checksum.slice(0, 12)}…
                      </small>
                    )}
                  </div>
                  <button
                    className={`button ${
                      acknowledgementQuery.data.acknowledged ? "ghost" : "primary"
                    }`}
                    type="button"
                    disabled={
                      acknowledgementQuery.data.acknowledged || acknowledgeDocument.isPending
                    }
                    onClick={() => acknowledgeDocument.mutate()}
                  >
                    <BadgeCheck size={15} />{" "}
                    {acknowledgementQuery.data.acknowledged
                      ? "Ciência registrada"
                      : acknowledgeDocument.isPending
                        ? "Registrando…"
                        : "Li e estou ciente"}
                  </button>
                  {acknowledgeDocument.isError && (
                    <div className="form-error acknowledgement-error">
                      {acknowledgeDocument.error instanceof ApiError
                        ? acknowledgeDocument.error.message
                        : "Não foi possível registrar a ciência."}
                    </div>
                  )}
                </section>
              )}
              <section className="rag-panel">
                <div className="rag-heading">
                  <Bot size={24} />
                  <div>
                    <h2>Pergunte ao documento</h2>
                    <p>
                      {documentQuery.data?.status === "READY"
                        ? `${documentQuery.data.page_count} páginas indexadas com fontes verificáveis.`
                        : "A pergunta será liberada quando a indexação estiver pronta."}
                    </p>
                  </div>
                </div>
                <div className="rag-question">
                  <textarea
                    rows={3}
                    value={question}
                    maxLength={1000}
                    placeholder="Ex.: Qual é o procedimento recomendado para comunicar um incidente?"
                    onChange={(event) => setQuestion(event.target.value)}
                  />
                  <button
                    className="button primary"
                    type="button"
                    disabled={
                      question.trim().length < 3 ||
                      askDocument.isPending ||
                      documentQuery.data?.status !== "READY"
                    }
                    onClick={() => askDocument.mutate()}
                  >
                    <Send size={15} /> {askDocument.isPending ? "Consultando…" : "Perguntar"}
                  </button>
                </div>
                {ragError && <div className="form-error">{ragError}</div>}
                {askDocument.data && (
                  <div className="rag-answer" aria-live="polite">
                    <strong>Resposta</strong>
                    <p>{askDocument.data.answer}</p>
                    <div className="rag-sources">
                      <span>Fontes</span>
                      {askDocument.data.sources.map((source) => (
                        <details key={`${source.document_version_id}-${source.page}`}>
                          <summary>
                            {source.title} · página {source.page}
                          </summary>
                          <p>{source.excerpt}</p>
                        </details>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </>
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
            <button
              className="text-button"
              type="button"
              disabled={progress.isPending}
              onClick={() => progress.mutate(50)}
            >
              Salvar progresso em 50%
            </button>
          )}
          {progress.isError && (
            <div className="form-error sidebar-feedback" role="alert">
              Não foi possível salvar o progresso. Tente novamente.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
