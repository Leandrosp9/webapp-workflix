import { CheckCircle2, Plus, UserRoundPlus, Users } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "../../components/PageState";
import { ApiError, api } from "../../services/http";
import type { User, UserSummary } from "../../types/api";

export default function AdminUsersPage() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "Workflix@2026" });
  const [error, setError] = useState("");
  const query = useQuery({ queryKey: ["users"], queryFn: () => api<UserSummary[]>("/users") });
  const create = useMutation({
    mutationFn: () => api<User>("/users", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: () => {
      setOpen(false);
      setForm({ full_name: "", email: "", password: "Workflix@2026" });
      void client.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (reason) =>
      setError(reason instanceof ApiError ? reason.message : "Não foi possível criar."),
  });
  if (query.isLoading) return <LoadingState />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const average = query.data.length
    ? Math.round(
        query.data.reduce((total, user) => total + user.completion_percent, 0) / query.data.length,
      )
    : 0;
  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Equipe NovaTech</span>
          <h1>Colaboradores</h1>
          <p>Gerencie acessos e acompanhe o desenvolvimento individual.</p>
        </div>
        <button className="button primary" type="button" onClick={() => setOpen(true)}>
          <Plus size={16} /> Novo colaborador
        </button>
      </div>
      <div className="people-summary">
        <span>
          <Users /> <strong>{query.data.length}</strong> colaboradores
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
              <th>Atribuídos</th>
              <th>Concluídos</th>
              <th>Pendentes</th>
              <th>Progresso</th>
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
                    </div>
                  </div>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open && (
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
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                required
                minLength={2}
              />
            </label>
            <label>
              E-mail corporativo
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                required
              />
            </label>
            <label>
              Senha inicial
              <input
                type="text"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                required
                minLength={8}
              />
            </label>
            {error && <div className="form-error">{error}</div>}
            <div className="modal-actions">
              <button className="button ghost" type="button" onClick={() => setOpen(false)}>
                Cancelar
              </button>
              <button className="button primary" type="submit" disabled={create.isPending}>
                {create.isPending ? "Criando…" : "Criar acesso"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
