import { Plus, Search, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../../components/PageState";
import { TrainingCard } from "../../components/TrainingCard";
import { api } from "../../services/http";
import type { Training } from "../../types/api";

export default function AdminTrainingsPage() {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["admin-trainings"],
    queryFn: () => api<Training[]>("/trainings"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/trainings/${id}`, { method: "DELETE" }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["admin-trainings"] }),
  });
  const filtered = useMemo(
    () =>
      query.data?.filter((training) =>
        training.title.toLowerCase().includes(search.toLowerCase()),
      ) ?? [],
    [query.data, search],
  );
  if (query.isLoading) return <LoadingState />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Catálogo corporativo</span>
          <h1>Treinamentos</h1>
          <p>Crie, publique e acompanhe todo o conteúdo da empresa.</p>
        </div>
        <Link className="button primary" to="/admin/trainings/new">
          <Plus size={16} /> Novo treinamento
        </Link>
      </div>
      <div className="toolbar">
        <label className="search-field">
          <Search size={16} />
          <input
            placeholder="Buscar treinamento"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <span>{filtered.length} conteúdos</span>
      </div>
      <div className="admin-training-grid">
        {filtered.map((training) => (
          <div key={training.id} className="admin-training-item">
            <TrainingCard training={training} admin />
            <button
              type="button"
              className="delete-training"
              aria-label={`Excluir ${training.title}`}
              onClick={() => {
                if (window.confirm(`Excluir “${training.title}”?`)) remove.mutate(training.id);
              }}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
