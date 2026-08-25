import { CheckCircle2, Pencil, Plus, UserCheck, UserRoundPlus, Users, UserX } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "../../components/PageState";
import { ApiError, api } from "../../services/http";
import type { User, UserSummary } from "../../types/api";

type UserDialog =
  | { mode: "create" }
  | { mode: "edit"; user: UserSummary }
  | { mode: "status"; user: UserSummary }
  | null;

interface UserPatch {
  full_name?: string;
  email?: string;
  cpf?: string;
  is_active?: boolean;
}

function formatCpf(value: string) {
  return value
    .replace(/\D/g, "")
    .slice(0, 11)
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export default function AdminUsersPage() {
  const client = useQueryClient();
  const [dialog, setDialog] = useState<UserDialog>(null);
  const [createForm, setCreateForm] = useState({
    full_name: "",
    email: "",
    cpf: "",
    password: "Workflix@2026",
  });
  const [editForm, setEditForm] = useState({ full_name: "", email: "", cpf: "" });
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const query = useQuery({ queryKey: ["users"], queryFn: () => api<UserSummary[]>("/users") });
  const create = useMutation({
    mutationFn: () => api<User>("/users", { method: "POST", body: JSON.stringify(createForm) }),
    onSuccess: () => {
      setDialog(null);
      setCreateForm({ full_name: "", email: "", cpf: "", password: "Workflix@2026" });
      setFeedback("Colaborador adicionado e acesso liberado.");
      void client.invalidateQueries({ queryKey: ["users"] });
    },
    onError: showMutationError,
  });
  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UserPatch }) =>
      api<User>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: (user, variables) => {
      setDialog(null);
      setFeedback(
        variables.payload.is_active === undefined
          ? `Dados de ${user.full_name} atualizados.`
          : `Acesso de ${user.full_name} ${user.is_active ? "ativado" : "inativado"}.`,
      );
      void client.invalidateQueries({ queryKey: ["users"] });
    },
    onError: showMutationError,
  });

  function showMutationError(reason: unknown) {
    setError(reason instanceof ApiError ? reason.message : "Não foi possível concluir a ação.");
  }

  function openEdit(user: UserSummary) {
    setError("");
    setFeedback("");
    setEditForm({ full_name: user.full_name, email: user.email, cpf: formatCpf(user.cpf ?? "") });
    setDialog({ mode: "edit", user });
  }

  if (query.isLoading) return <LoadingState />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const average = query.data.length
    ? Math.round(
        query.data.reduce((total, user) => total + user.completion_percent, 0) / query.data.length,
      )
    : 0;
  const activeUsers = query.data.filter((user) => user.is_active).length;

  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Equipe NovaTech</span>
          <h1>Colaboradores</h1>
          <p>Gerencie acessos e acompanhe o desenvolvimento individual.</p>
        </div>
        <button
          className="button primary"
          type="button"
          onClick={() => {
            setError("");
            setFeedback("");
            setDialog({ mode: "create" });
          }}
        >
          <Plus size={16} /> Novo colaborador
        </button>
      </div>
      {feedback && (
        <div className="form-message global-message" role="status">
          {feedback}
        </div>
      )}
      <div className="people-summary">
        <span>
          <Users /> <strong>{query.data.length}</strong> colaboradores
        </span>
        <span>
          <UserCheck /> <strong>{activeUsers}</strong> acessos ativos
        </span>
        <span>
          <CheckCircle2 /> <strong>{average}%</strong> conclusão média
        </span>
      </div>
      <div className="people-table-wrap">
        <table className="people-table">
          <thead>
            <tr>
              <th>Colaborador</th>
              <th>Status</th>
              <th>Atribuídos</th>
              <th>Concluídos</th>
              <th>Pendentes</th>
              <th>Progresso</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {query.data.map((user) => (
              <tr key={user.id}>
                <td>
                  <div className="person-cell">
                    <span className="avatar">{user.full_name[0]}</span>
                    <div>
                      <strong>{user.full_name}</strong>
                      <small>{user.email}</small>
                      <small>CPF {user.cpf ? formatCpf(user.cpf) : "não informado"}</small>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`people-status ${user.is_active ? "active" : "inactive"}`}>
                    {user.is_active ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td>{user.assigned}</td>
                <td>{user.completed}</td>
                <td>{user.pending}</td>
                <td>
                  <div className="table-progress">
                    <span>
                      <i style={{ width: `${user.completion_percent}%` }} />
                    </span>
                    <strong>{user.completion_percent}%</strong>
                  </div>
                </td>
                <td>
                  <div className="people-actions">
                    <button
                      type="button"
                      aria-label={`Editar ${user.full_name}`}
                      title="Editar colaborador"
                      onClick={() => openEdit(user)}
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      aria-label={`${user.is_active ? "Inativar" : "Ativar"} ${user.full_name}`}
                      title={user.is_active ? "Inativar acesso" : "Ativar acesso"}
                      onClick={() => {
                        setError("");
                        setFeedback("");
                        setDialog({ mode: "status", user });
                      }}
                    >
                      {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {dialog?.mode === "create" && (
        <div className="modal-backdrop" role="presentation">
          <form
            className="modal"
            onSubmit={(event) => {
              event.preventDefault();
              setError("");
              create.mutate();
            }}
          >
            <div className="modal-icon">
              <UserRoundPlus />
            </div>
            <span className="section-kicker">Novo acesso</span>
            <h2>Adicionar colaborador</h2>
            <label>
              Nome completo
              <input
                value={createForm.full_name}
                onChange={(event) =>
                  setCreateForm({ ...createForm, full_name: event.target.value })
                }
                required
                minLength={2}
              />
            </label>
            <label>
              CPF
              <input
                inputMode="numeric"
                value={createForm.cpf}
                placeholder="000.000.000-00"
                onChange={(event) =>
                  setCreateForm({ ...createForm, cpf: formatCpf(event.target.value) })
                }
                required
                minLength={14}
              />
            </label>
            <label>
              E-mail corporativo
              <input
                type="email"
                value={createForm.email}
                onChange={(event) => setCreateForm({ ...createForm, email: event.target.value })}
                required
              />
            </label>
            <label>
              Senha inicial
              <input
                type="text"
                value={createForm.password}
                onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })}
                required
                minLength={8}
              />
            </label>
            {error && <div className="form-error">{error}</div>}
            <div className="modal-actions">
              <button className="button ghost" type="button" onClick={() => setDialog(null)}>
                Cancelar
              </button>
              <button className="button primary" type="submit" disabled={create.isPending}>
                {create.isPending ? "Criando…" : "Criar acesso"}
              </button>
            </div>
          </form>
        </div>
      )}

      {dialog?.mode === "edit" && (
        <div className="modal-backdrop" role="presentation">
          <form
            className="modal"
            onSubmit={(event) => {
              event.preventDefault();
              setError("");
              update.mutate({ id: dialog.user.id, payload: editForm });
            }}
          >
            <div className="modal-icon">
              <Pencil />
            </div>
            <span className="section-kicker">Editar cadastro</span>
            <h2>Dados do colaborador</h2>
            <label>
              Nome completo
              <input
                value={editForm.full_name}
                onChange={(event) => setEditForm({ ...editForm, full_name: event.target.value })}
                required
                minLength={2}
              />
            </label>
            <label>
              CPF
              <input
                inputMode="numeric"
                value={editForm.cpf}
                placeholder="000.000.000-00"
                onChange={(event) =>
                  setEditForm({ ...editForm, cpf: formatCpf(event.target.value) })
                }
                required
                minLength={14}
              />
            </label>
            <label>
              E-mail corporativo
              <input
                type="email"
                value={editForm.email}
                onChange={(event) => setEditForm({ ...editForm, email: event.target.value })}
                required
              />
            </label>
            {error && <div className="form-error">{error}</div>}
            <div className="modal-actions">
              <button className="button ghost" type="button" onClick={() => setDialog(null)}>
                Cancelar
              </button>
              <button className="button primary" type="submit" disabled={update.isPending}>
                {update.isPending ? "Salvando…" : "Salvar alterações"}
              </button>
            </div>
          </form>
        </div>
      )}

      {dialog?.mode === "status" && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="status-title">
            <div className="modal-icon">{dialog.user.is_active ? <UserX /> : <UserCheck />}</div>
            <span className="section-kicker">Controle de acesso</span>
            <h2 id="status-title">
              {dialog.user.is_active ? "Inativar colaborador?" : "Ativar colaborador?"}
            </h2>
            <p className="modal-copy">
              {dialog.user.is_active
                ? `${dialog.user.full_name} perderá o acesso imediatamente, sem apagar o histórico.`
                : `${dialog.user.full_name} poderá entrar novamente e manterá todo o histórico.`}
            </p>
            {error && <div className="form-error">{error}</div>}
            <div className="modal-actions">
              <button className="button ghost" type="button" onClick={() => setDialog(null)}>
                Cancelar
              </button>
              <button
                className={`button ${dialog.user.is_active ? "danger" : "primary"}`}
                type="button"
                disabled={update.isPending}
                onClick={() =>
                  update.mutate({
                    id: dialog.user.id,
                    payload: { is_active: !dialog.user.is_active },
                  })
                }
              >
                {update.isPending
                  ? "Atualizando…"
                  : dialog.user.is_active
                    ? "Confirmar inativação"
                    : "Confirmar ativação"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
