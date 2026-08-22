import { ArrowDown, ArrowUp, Check, ListChecks, Plus, Send, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { ErrorState, LoadingState } from "../../components/PageState";
import { ApiError, api } from "../../services/http";
import type { LearningPath, Training, UserSummary } from "../../types/api";

interface DraftItem {
  training_id: string;
  required: boolean;
}

export default function AdminLearningPathsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftItems, setDraftItems] = useState<DraftItem[]>([]);
  const [employeeIds, setEmployeeIds] = useState<string[]>([]);
  const [dueDate, setDueDate] = useState("");
  const [form, setForm] = useState({ title: "", description: "" });
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const paths = useQuery({
    queryKey: ["learning-paths"],
    queryFn: () => api<LearningPath[]>("/learning-paths"),
  });
  const trainings = useQuery({
    queryKey: ["admin-trainings"],
    queryFn: () => api<Training[]>("/trainings"),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<UserSummary[]>("/users"),
  });
  const selected = useMemo(
    () => paths.data?.find((path) => path.id === selectedId) ?? null,
    [paths.data, selectedId],
  );

  useEffect(() => {
    if (!selected) return;
    setForm({ title: selected.title, description: selected.description });
    setDraftItems(
      selected.items.map((item) => ({ training_id: item.training_id, required: item.required })),
    );
  }, [selected]);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["learning-paths"] });
  };
  const create = useMutation({
    mutationFn: () =>
      api<LearningPath>("/learning-paths", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: async (path) => {
      setSelectedId(path.id);
      setMessageIsError(false);
      setMessage("Trilha criada como rascunho. Agora ordene os conteúdos.");
      await refresh();
    },
    onError: showError,
  });
  const save = useMutation({
    mutationFn: async () => {
      if (!selected) return;
      await api(`/learning-paths/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify(form),
      });
      await api(`/learning-paths/${selected.id}/items`, {
        method: "PUT",
        body: JSON.stringify({ items: draftItems }),
      });
    },
    onSuccess: async () => {
      setMessageIsError(false);
      setMessage("Conteúdos e ordem salvos.");
      await refresh();
    },
    onError: showError,
  });
  const publish = useMutation({
    mutationFn: () =>
      api(`/learning-paths/${selected?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "PUBLISHED" }),
      }),
    onSuccess: async () => {
      setMessageIsError(false);
      setMessage("Trilha publicada e pronta para atribuição.");
      await refresh();
    },
    onError: showError,
  });
  const assign = useMutation({
    mutationFn: () =>
      api(`/learning-paths/${selected?.id}/assignments`, {
        method: "POST",
        body: JSON.stringify({ employee_ids: employeeIds, due_date: dueDate || null }),
      }),
    onSuccess: async () => {
      setMessageIsError(false);
      setMessage("Trilha atribuída. Os treinamentos já estão disponíveis aos colaboradores.");
      setEmployeeIds([]);
      await refresh();
    },
    onError: showError,
  });

  function showError(reason: unknown) {
    setMessageIsError(true);
    setMessage(reason instanceof ApiError ? reason.message : "Não foi possível concluir.");
  }

  if (paths.isLoading || trainings.isLoading || users.isLoading) return <LoadingState />;
  if (!paths.data || !trainings.data || !users.data) {
    return <ErrorState retry={() => void paths.refetch()} />;
  }
  const publishedTrainings = trainings.data.filter((training) => training.status === "PUBLISHED");
  const available = publishedTrainings.filter(
    (training) => !draftItems.some((item) => item.training_id === training.id),
  );

  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Jornadas de desenvolvimento</span>
          <h1>Trilhas</h1>
          <p>Organize conteúdos em sequência, publique e atribua para a equipe.</p>
        </div>
        <button
          className="button primary"
          type="button"
          onClick={() => {
            setSelectedId(null);
            setForm({ title: "", description: "" });
            setDraftItems([]);
            setMessage("");
            setMessageIsError(false);
          }}
        >
          <Plus size={16} /> Nova trilha
        </button>
      </div>
      {message && (
        <div
          className={`${messageIsError ? "form-error" : "form-message"} global-message`}
          role={messageIsError ? "alert" : "status"}
        >
          {message}
        </div>
      )}
      <div className="path-admin-layout">
        <aside className="path-list panel-card">
          <span className="section-kicker">Trilhas cadastradas</span>
          {paths.data.length === 0 && <p>Nenhuma trilha criada.</p>}
          {paths.data.map((path) => (
            <button
              type="button"
              key={path.id}
              className={selectedId === path.id ? "active" : ""}
              onClick={() => setSelectedId(path.id)}
            >
              <ListChecks size={17} />
              <span>
                <strong>{path.title}</strong>
                <small>
                  {path.items.length} conteúdos · {path.assignment_count} atribuídos
                </small>
              </span>
              <i className={`status-badge ${path.status.toLowerCase()}`}>{path.status}</i>
            </button>
          ))}
        </aside>

        <section className="path-editor panel-card">
          <div className="card-heading">
            <div>
              <span className="section-kicker">{selected ? "Editar trilha" : "Nova trilha"}</span>
              <h2>{selected?.title ?? "Defina o ponto de partida"}</h2>
            </div>
            {selected?.status === "PUBLISHED" && <Check className="success-icon" />}
          </div>
          <div className="editor-form-grid">
            <label>
              Nome
              <input
                value={form.title}
                minLength={3}
                disabled={selected?.status === "PUBLISHED"}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </label>
            <label className="full">
              Descrição
              <textarea
                value={form.description}
                disabled={selected?.status === "PUBLISHED"}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </label>
          </div>
          {selected?.status === "PUBLISHED" && (
            <p className="form-note">
              Trilha publicada: a estrutura permanece bloqueada para preservar as atribuições.
            </p>
          )}
          {!selected ? (
            <button
              className="button primary path-primary-action"
              type="button"
              disabled={create.isPending || form.title.trim().length < 3}
              onClick={() => create.mutate()}
            >
              Criar rascunho
            </button>
          ) : selected.status === "DRAFT" ? (
            <>
              <div className="path-builder">
                <div className="path-builder-column">
                  <h3>Conteúdos disponíveis</h3>
                  {available.map((training) => (
                    <button
                      key={training.id}
                      type="button"
                      onClick={() =>
                        setDraftItems([...draftItems, { training_id: training.id, required: true }])
                      }
                    >
                      <Plus size={14} /> <span>{training.title}</span>
                    </button>
                  ))}
                  {available.length === 0 && (
                    <small>Todos os conteúdos publicados já estão na trilha.</small>
                  )}
                </div>
                <div className="path-builder-column ordered">
                  <h3>Ordem da trilha</h3>
                  {draftItems.map((item, index) => {
                    const training = trainings.data.find(
                      (candidate) => candidate.id === item.training_id,
                    );
                    return (
                      <div key={item.training_id}>
                        <b>{index + 1}</b>
                        <span>{training?.title}</span>
                        <label title="Obrigatório">
                          <input
                            type="checkbox"
                            checked={item.required}
                            onChange={(event) =>
                              setDraftItems(
                                draftItems.map((candidate, position) =>
                                  position === index
                                    ? { ...candidate, required: event.target.checked }
                                    : candidate,
                                ),
                              )
                            }
                          />
                          obrigatório
                        </label>
                        <button
                          type="button"
                          aria-label="Mover para cima"
                          disabled={index === 0}
                          onClick={() => setDraftItems(move(draftItems, index, index - 1))}
                        >
                          <ArrowUp size={13} />
                        </button>
                        <button
                          type="button"
                          aria-label="Mover para baixo"
                          disabled={index === draftItems.length - 1}
                          onClick={() => setDraftItems(move(draftItems, index, index + 1))}
                        >
                          <ArrowDown size={13} />
                        </button>
                        <button
                          type="button"
                          aria-label="Remover"
                          onClick={() =>
                            setDraftItems(draftItems.filter((_, position) => position !== index))
                          }
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="path-actions">
                <button
                  className="button secondary"
                  type="button"
                  disabled={save.isPending || draftItems.length === 0}
                  onClick={() => save.mutate()}
                >
                  Salvar ordem
                </button>
                <button
                  className="button primary"
                  type="button"
                  disabled={publish.isPending || selected.items.length === 0}
                  onClick={() => publish.mutate()}
                >
                  Publicar trilha
                </button>
              </div>
            </>
          ) : (
            <div className="path-assignment">
              <h3>Atribuir trilha publicada</h3>
              <div className="employee-picker">
                {users.data.map((user) => (
                  <label key={user.id}>
                    <input
                      type="checkbox"
                      checked={employeeIds.includes(user.id)}
                      onChange={(event) =>
                        setEmployeeIds(
                          event.target.checked
                            ? [...employeeIds, user.id]
                            : employeeIds.filter((id) => id !== user.id),
                        )
                      }
                    />
                    <span>
                      <strong>{user.full_name}</strong>
                      <small>{user.email}</small>
                    </span>
                  </label>
                ))}
              </div>
              <div className="path-actions">
                <label>
                  Prazo opcional
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(event) => setDueDate(event.target.value)}
                  />
                </label>
                <button
                  className="button primary"
                  type="button"
                  disabled={assign.isPending || employeeIds.length === 0}
                  onClick={() => assign.mutate()}
                >
                  <Send size={15} /> Atribuir a {employeeIds.length || 0}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function move<T>(items: T[], from: number, to: number): T[] {
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
