import { ArrowLeft, FileUp, Plus, Save, Sparkles, Trash2, Users } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { LoadingState } from "../../components/PageState";
import { ApiError, api } from "../../services/http";
import type { Training, TrainingStatus, TrainingType, UserSummary } from "../../types/api";

interface TrainingForm {
  title: string;
  description: string;
  type: TrainingType;
  content: string;
  video_url: string;
  thumbnail_url: string;
  estimated_minutes: number;
  status: TrainingStatus;
}

interface QuizDraft {
  passing_score: number;
  questions: Array<{
    text: string;
    explanation: string;
    options: Array<{ text: string; is_correct: boolean }>;
  }>;
}

const emptyForm: TrainingForm = {
  title: "",
  description: "",
  type: "ARTICLE",
  content: "",
  video_url: "",
  thumbnail_url: "",
  estimated_minutes: 15,
  status: "DRAFT",
};

const emptyQuiz = (): QuizDraft => ({
  passing_score: 70,
  questions: [
    {
      text: "",
      explanation: "",
      options: [
        { text: "", is_correct: true },
        { text: "", is_correct: false },
      ],
    },
  ],
});

export default function AdminTrainingEditorPage() {
  const { trainingId } = useParams();
  const isNew = !trainingId || trainingId === "new";
  const navigate = useNavigate();
  const client = useQueryClient();
  const [form, setForm] = useState<TrainingForm>(emptyForm);
  const [quiz, setQuiz] = useState<QuizDraft>(emptyQuiz);
  const [selectedEmployees, setSelectedEmployees] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const trainingQuery = useQuery({
    queryKey: ["admin-training", trainingId],
    queryFn: () => api<Training>(`/trainings/${trainingId}`),
    enabled: !isNew,
  });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: () => api<UserSummary[]>("/users") });
  const quizQuery = useQuery({
    queryKey: ["admin-quiz", trainingId],
    queryFn: () => api<QuizDraft>(`/trainings/${trainingId}/quiz`),
    enabled: !isNew && Boolean(trainingQuery.data?.has_quiz),
    retry: false,
  });

  useEffect(() => {
    const training = trainingQuery.data;
    if (!training) return;
    setForm({
      title: training.title,
      description: training.description,
      type: training.type,
      content: training.content,
      video_url: training.video_url ?? "",
      thumbnail_url: training.thumbnail_url ?? "",
      estimated_minutes: training.estimated_minutes,
      status: training.status,
    });
  }, [trainingQuery.data]);
  useEffect(() => {
    if (quizQuery.data) setQuiz(quizQuery.data);
  }, [quizQuery.data]);

  const saveTraining = useMutation({
    mutationFn: () =>
      api<Training>(isNew ? "/trainings" : `/trainings/${trainingId}`, {
        method: isNew ? "POST" : "PATCH",
        body: JSON.stringify({
          ...form,
          video_url: form.video_url || null,
          thumbnail_url: form.thumbnail_url || null,
        }),
      }),
    onSuccess: (saved) => {
      setMessage("Treinamento salvo.");
      void client.invalidateQueries({ queryKey: ["admin-trainings"] });
      if (isNew) void navigate(`/admin/trainings/${saved.id}`, { replace: true });
    },
    onError: handleError,
  });
  const generateTraining = useMutation({
    mutationFn: () =>
      api<{ draft: Pick<TrainingForm, "title" | "description" | "content" | "estimated_minutes"> }>(
        "/ai/generate-training",
        {
          method: "POST",
          body: JSON.stringify({
            topic: form.title || "Novo treinamento corporativo",
            audience: "Colaboradores da empresa",
            learning_objectives: [form.description || "Aplicar o conhecimento no trabalho"],
            estimated_minutes: form.estimated_minutes,
          }),
        },
      ),
    onSuccess: ({ draft }) => setForm((current) => ({ ...current, ...draft, type: "ARTICLE" })),
    onError: handleError,
  });
  const saveQuiz = useMutation({
    mutationFn: () =>
      api<QuizDraft>(`/trainings/${trainingId}/quiz`, {
        method: "PUT",
        body: JSON.stringify(quiz),
      }),
    onSuccess: (saved) => {
      setQuiz(saved);
      setMessage("Avaliação salva.");
    },
    onError: handleError,
  });
  const generateQuiz = useMutation({
    mutationFn: () =>
      api<{ draft: QuizDraft }>("/ai/generate-quiz", {
        method: "POST",
        body: JSON.stringify({
          training_id: trainingId,
          question_count: 5,
          passing_score: quiz.passing_score,
        }),
      }),
    onSuccess: ({ draft }) => setQuiz(draft),
    onError: handleError,
  });
  const assign = useMutation({
    mutationFn: () =>
      api<{ assigned: number; updated: number }>(`/trainings/${trainingId}/assignments`, {
        method: "POST",
        body: JSON.stringify({ employee_ids: selectedEmployees }),
      }),
    onSuccess: ({ assigned, updated }) =>
      setMessage(`${assigned} novas atribuições e ${updated} atualizadas.`),
    onError: handleError,
  });
  const uploadPdf = useMutation({
    mutationFn: (file: File) => {
      const data = new FormData();
      data.append("file", file);
      return api<Training>(`/trainings/${trainingId}/pdf`, { method: "POST", body: data });
    },
    onSuccess: () => {
      setForm((current) => ({ ...current, type: "PDF" }));
      setMessage("PDF enviado com segurança.");
    },
    onError: handleError,
  });

  function handleError(reason: unknown) {
    setError(reason instanceof ApiError ? reason.message : "Não foi possível concluir a operação.");
  }
  function updateQuestion(questionIndex: number, field: "text" | "explanation", value: string) {
    setQuiz((current) => ({
      ...current,
      questions: current.questions.map((question, index) =>
        index === questionIndex ? { ...question, [field]: value } : question,
      ),
    }));
  }
  function updateOption(questionIndex: number, optionIndex: number, value: string) {
    setQuiz((current) => ({
      ...current,
      questions: current.questions.map((question, index) =>
        index === questionIndex
          ? {
              ...question,
              options: question.options.map((option, position) =>
                position === optionIndex ? { ...option, text: value } : option,
              ),
            }
          : question,
      ),
    }));
  }

  if (!isNew && trainingQuery.isLoading) return <LoadingState />;
  return (
    <div className="editor-page">
      <Link className="back-link" to="/admin/trainings">
        <ArrowLeft size={16} /> Voltar para treinamentos
      </Link>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Editor de conteúdo</span>
          <h1>{isNew ? "Novo treinamento" : form.title || "Editar treinamento"}</h1>
          <p>Construa a experiência, defina a avaliação e atribua à equipe.</p>
        </div>
        <div className="editor-heading-actions">
          <button
            className="button secondary"
            type="button"
            onClick={() => generateTraining.mutate()}
            disabled={generateTraining.isPending}
          >
            <Sparkles size={16} /> {generateTraining.isPending ? "Gerando…" : "Criar com Gemini"}
          </button>
          <button
            className="button primary"
            type="button"
            onClick={() => saveTraining.mutate()}
            disabled={saveTraining.isPending}
          >
            <Save size={16} /> Salvar
          </button>
        </div>
      </div>
      {error && <div className="form-error global-message">{error}</div>}
      {message && <div className="success-message">{message}</div>}
      <section className="editor-card">
        <div className="editor-card-heading">
          <span>01</span>
          <div>
            <h2>Informações principais</h2>
            <p>O que as pessoas verão no catálogo.</p>
          </div>
        </div>
        <div className="editor-form-grid">
          <label className="full">
            Título
            <input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
          </label>
          <label className="full">
            Descrição
            <textarea
              rows={3}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          <label>
            Formato
            <select
              value={form.type}
              onChange={(event) => setForm({ ...form, type: event.target.value as TrainingType })}
            >
              <option value="ARTICLE">Artigo</option>
              <option value="VIDEO">Vídeo</option>
              <option value="PDF">PDF</option>
            </select>
          </label>
          <label>
            Duração estimada
            <input
              type="number"
              min={1}
              value={form.estimated_minutes}
              onChange={(event) =>
                setForm({ ...form, estimated_minutes: Number(event.target.value) })
              }
            />
          </label>
          <label>
            Status
            <select
              value={form.status}
              onChange={(event) =>
                setForm({ ...form, status: event.target.value as TrainingStatus })
              }
            >
              <option value="DRAFT">Rascunho</option>
              <option value="PUBLISHED">Publicado</option>
            </select>
          </label>
          <label>
            Imagem de capa (URL)
            <input
              value={form.thumbnail_url}
              onChange={(event) => setForm({ ...form, thumbnail_url: event.target.value })}
            />
          </label>
          {form.type === "VIDEO" && (
            <label className="full">
              URL do vídeo
              <input
                value={form.video_url}
                onChange={(event) => setForm({ ...form, video_url: event.target.value })}
              />
            </label>
          )}
          <label className="full">
            Conteúdo
            <textarea
              className="content-editor"
              rows={16}
              value={form.content}
              onChange={(event) => setForm({ ...form, content: event.target.value })}
              placeholder="Escreva em Markdown…"
            />
          </label>
          {!isNew && (
            <label className="pdf-upload full">
              <FileUp />
              <span>
                <strong>Enviar material PDF</strong>
                <small>Máximo configurado no servidor; validação por tipo e assinatura.</small>
              </span>
              <input
                type="file"
                accept="application/pdf"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) uploadPdf.mutate(file);
                }}
              />
            </label>
          )}
        </div>
      </section>
      {!isNew && (
        <section className="editor-card">
          <div className="editor-card-heading">
            <span>02</span>
            <div>
              <h2>Avaliação</h2>
              <p>Questões de múltipla escolha corrigidas no servidor.</p>
            </div>
            <button
              className="button secondary"
              type="button"
              onClick={() => generateQuiz.mutate()}
              disabled={generateQuiz.isPending}
            >
              <Sparkles size={15} /> {generateQuiz.isPending ? "Gerando…" : "Gerar 5 questões"}
            </button>
          </div>
          <label className="passing-field">
            Nota mínima
            <input
              type="number"
              min={0}
              max={100}
              value={quiz.passing_score}
              onChange={(event) => setQuiz({ ...quiz, passing_score: Number(event.target.value) })}
            />
          </label>
          <div className="question-editor-list">
            {quiz.questions.map((question, questionIndex) => (
              <div className="question-editor" key={`${questionIndex}-${question.text}`}>
                <div className="question-editor-title">
                  <strong>Questão {questionIndex + 1}</strong>
                  {quiz.questions.length > 1 && (
                    <button
                      type="button"
                      onClick={() =>
                        setQuiz({
                          ...quiz,
                          questions: quiz.questions.filter((_, index) => index !== questionIndex),
                        })
                      }
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                <input
                  placeholder="Enunciado"
                  value={question.text}
                  onChange={(event) => updateQuestion(questionIndex, "text", event.target.value)}
                />
                <input
                  placeholder="Explicação após a resposta"
                  value={question.explanation}
                  onChange={(event) =>
                    updateQuestion(questionIndex, "explanation", event.target.value)
                  }
                />
                {question.options.map((option, optionIndex) => (
                  <label className="option-editor" key={optionIndex}>
                    <input
                      type="radio"
                      name={`correct-${questionIndex}`}
                      checked={option.is_correct}
                      onChange={() =>
                        setQuiz((current) => ({
                          ...current,
                          questions: current.questions.map((item, index) =>
                            index === questionIndex
                              ? {
                                  ...item,
                                  options: item.options.map((entry, position) => ({
                                    ...entry,
                                    is_correct: position === optionIndex,
                                  })),
                                }
                              : item,
                          ),
                        }))
                      }
                    />
                    <input
                      value={option.text}
                      placeholder={`Alternativa ${optionIndex + 1}`}
                      onChange={(event) =>
                        updateOption(questionIndex, optionIndex, event.target.value)
                      }
                    />
                  </label>
                ))}
              </div>
            ))}
          </div>
          <div className="editor-footer">
            <button
              className="button ghost"
              type="button"
              onClick={() =>
                setQuiz({ ...quiz, questions: [...quiz.questions, emptyQuiz().questions[0]] })
              }
            >
              <Plus size={15} /> Adicionar questão
            </button>
            <button className="button primary" type="button" onClick={() => saveQuiz.mutate()}>
              <Save size={15} /> Salvar avaliação
            </button>
          </div>
        </section>
      )}
      {!isNew && (
        <section className="editor-card">
          <div className="editor-card-heading">
            <span>03</span>
            <div>
              <h2>Atribuir à equipe</h2>
              <p>Selecione os colaboradores que devem receber este conteúdo.</p>
            </div>
            <Users />
          </div>
          <div className="employee-selector">
            {usersQuery.data?.map((user) => (
              <label key={user.id}>
                <input
                  type="checkbox"
                  checked={selectedEmployees.includes(user.id)}
                  onChange={(event) =>
                    setSelectedEmployees((current) =>
                      event.target.checked
                        ? [...current, user.id]
                        : current.filter((id) => id !== user.id),
                    )
                  }
                />
                <span className="avatar">{user.full_name[0]}</span>
                <span>
                  <strong>{user.full_name}</strong>
                  <small>{user.email}</small>
                </span>
              </label>
            ))}
          </div>
          <div className="editor-footer">
            <span>{selectedEmployees.length} selecionados</span>
            <button
              className="button primary"
              type="button"
              disabled={!selectedEmployees.length || assign.isPending}
              onClick={() => assign.mutate()}
            >
              Atribuir treinamento
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
