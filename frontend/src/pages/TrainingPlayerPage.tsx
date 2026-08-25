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
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { ApiError, api, downloadPdf } from "../services/http";
import type {
  DocumentVersion,
  EmployeeAcknowledgementStatus,
  RagAnswer,
  Training,
} from "../types/api";

function youtubeEmbedUrl(videoUrl: string | null) {
  if (!videoUrl) return null;
  try {
    const url = new URL(videoUrl);
    const hostname = url.hostname.replace(/^www\./, "");
    let videoId: string | null = null;

    if (hostname === "youtu.be") {
      videoId = url.pathname.split("/").filter(Boolean)[0] ?? null;
    } else if (hostname === "youtube.com" || hostname === "m.youtube.com") {
      if (url.pathname === "/watch") {
        videoId = url.searchParams.get("v");
      } else {
        const [kind, id] = url.pathname.split("/").filter(Boolean);
        if (["embed", "shorts", "live"].includes(kind)) videoId = id ?? null;
      }
    }

    return videoId && /^[\w-]{11}$/.test(videoId)
      ? `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`
      : null;
  } catch {
    return null;
  }
}

export default function TrainingPlayerPage() {
  const { trainingId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const contentRootRef = useRef<HTMLElement>(null);
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
      void queryClient.invalidateQueries({ queryKey: ["employee-certificates"] });
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

  useEffect(() => {
    const resumeStorageKey = `workflix.training.resume.${trainingId}`;
    const rememberPosition = () => {
      const content = contentRootRef.current?.querySelector<HTMLElement>("[data-learning-content]");
      if (!content) return;
      const contentTop = content.getBoundingClientRect().top + window.scrollY;
      if (window.scrollY + 160 >= contentTop) {
        window.localStorage.setItem(resumeStorageKey, String(Math.round(window.scrollY)));
      }
    };

    window.addEventListener("scroll", rememberPosition, { passive: true });
    return () => window.removeEventListener("scroll", rememberPosition);
  }, [trainingId]);

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

  function handleResume() {
    const currentTraining = query.data;
    if (currentTraining?.has_quiz && (currentTraining.progress_percent ?? 0) >= 50) {
      void navigate(`/app/training/${currentTraining.id}/quiz`);
      return;
    }

    const content = contentRootRef.current?.querySelector<HTMLElement>("[data-learning-content]");
    content?.focus({ preventScroll: true });
    const fallbackPosition = content
      ? content.getBoundingClientRect().top + window.scrollY - 88
      : 0;
    const savedPosition = Number.parseInt(
      window.localStorage.getItem(`workflix.training.resume.${trainingId}`) ?? "",
      10,
    );
    const requestedPosition =
      Number.isFinite(savedPosition) && savedPosition > 0 ? savedPosition : fallbackPosition;
    const maximumPosition = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);

    window.scrollTo({
      top: Math.max(0, Math.min(requestedPosition, maximumPosition)),
      behavior: "smooth",
    });
  }

  async function handleAdvance() {
    const currentTraining = query.data;
    if (!currentTraining) return;

    try {
      if (currentTraining.has_quiz) {
        if ((currentTraining.progress_percent ?? 0) < 50) {
          await progress.mutateAsync(50);
        }
        void navigate(`/app/training/${currentTraining.id}/quiz`);
        return;
      }

      await progress.mutateAsync(100);
      window.localStorage.removeItem(`workflix.training.resume.${currentTraining.id}`);
      void navigate("/app/certificates");
    } catch {
      // The mutation exposes the error in the page feedback and keeps the user on this step.
    }
  }

  if (query.isLoading) return <LoadingState label="Abrindo treinamento…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const training = query.data;
  const percent = training.progress_percent ?? 0;
  const videoEmbed = youtubeEmbedUrl(training.video_url);

  return (
    <div className="player-page">
      <Link className="back-link" to="/app">
        <ArrowLeft size={16} /> Voltar para início
      </Link>
      <div className="player-layout">
        <article ref={contentRootRef} className="player-content">
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
            <div
              className={`video-player${videoEmbed ? " has-embed" : ""}`}
              data-learning-content
              tabIndex={-1}
            >
              {videoEmbed ? (
                <>
                  <div className="video-embed">
                    <iframe
                      src={videoEmbed}
                      title={`Vídeo do treinamento ${training.title}`}
                      loading="lazy"
                      referrerPolicy="strict-origin-when-cross-origin"
                      allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                      sandbox="allow-scripts allow-same-origin allow-presentation"
                      allowFullScreen
                    />
                  </div>
                  <div className="video-player-footer">
                    <div>
                      <span className="section-kicker">Reprodução integrada</span>
                      <h2>Assista dentro do Workflix</h2>
                      <p>O conteúdo é reproduzido sem redirecionar você para outro site.</p>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <PlayCircle size={58} />
                  <h2>Vídeo indisponível para reprodução</h2>
                  <p>
                    {training.video_url
                      ? "Este endereço não permite reprodução segura dentro do Workflix."
                      : "O material de apoio deste treinamento está disponível abaixo."}
                  </p>
                </>
              )}
            </div>
          )}
          {training.type === "PDF" && training.has_pdf && (
            <>
              <div className="pdf-player" data-learning-content tabIndex={-1}>
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
          {training.content && (
            <div className="article-content" data-learning-content tabIndex={-1}>
              {training.content}
            </div>
          )}
          <nav className="learning-navigation" aria-label="Navegação do treinamento">
            <div className="learning-navigation-copy">
              <span className="section-kicker">
                {training.has_quiz ? "Etapa 1 de 2" : "Etapa única"}
              </span>
              <strong>
                {percent === 100
                  ? "Treinamento concluído"
                  : training.has_quiz
                    ? "Conteúdo concluído? Siga para a avaliação."
                    : "Concluiu a leitura? Finalize o treinamento."}
              </strong>
            </div>
            <div className="learning-navigation-actions">
              <Link className="button ghost" to="/app/catalog">
                <ArrowLeft size={16} /> Voltar aos treinamentos
              </Link>
              {percent === 100 ? (
                <Link className="button primary" to="/app">
                  Voltar ao início <ArrowRight size={16} />
                </Link>
              ) : (
                <button
                  className="button primary"
                  type="button"
                  disabled={progress.isPending}
                  onClick={() => void handleAdvance()}
                >
                  {progress.isPending
                    ? "Salvando avanço…"
                    : training.has_quiz
                      ? "Avançar para avaliação"
                      : "Concluir treinamento"}
                  {!progress.isPending &&
                    (training.has_quiz ? <ArrowRight size={16} /> : <CheckCircle2 size={16} />)}
                </button>
              )}
            </div>
          </nav>
        </article>
        <aside className="player-sidebar">
          <span className="section-kicker">Seu progresso</span>
          <strong>{percent}%</strong>
          <div className="large-progress">
            <span style={{ width: `${percent}%` }} />
          </div>
          {percent === 100 ? (
            <p>Treinamento concluído.</p>
          ) : (
            <>
              <p>
                {training.has_quiz && percent >= 50
                  ? "Seu conteúdo foi salvo. Continue pela avaliação."
                  : "Seu avanço fica salvo neste dispositivo."}
              </p>
              <button className="resume-button" type="button" onClick={handleResume}>
                {training.has_quiz && percent >= 50
                  ? "Continuar na avaliação"
                  : "Continuar de onde parou"}
                <ArrowRight size={14} />
              </button>
            </>
          )}
          {percent === 100 ? (
            <Link className="button primary" to="/app">
              Voltar ao início <ArrowRight size={16} />
            </Link>
          ) : (
            <button
              className="button primary"
              type="button"
              disabled={progress.isPending}
              onClick={() => void handleAdvance()}
            >
              {training.has_quiz ? <ArrowRight size={16} /> : <CheckCircle2 size={16} />}
              {progress.isPending
                ? "Salvando…"
                : training.has_quiz
                  ? "Avançar para avaliação"
                  : "Concluir treinamento"}
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
