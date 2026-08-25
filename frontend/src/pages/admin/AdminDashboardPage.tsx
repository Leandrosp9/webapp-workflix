import { ArrowRight, BookOpen, CheckCircle2, ClipboardList, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../../components/PageState";
import { api } from "../../services/http";
import type { Dashboard } from "../../types/api";
import { publicationStatusLabel, trainingTypeLabel } from "../../utils/labels";

export default function AdminDashboardPage() {
  const query = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: () => api<Dashboard>("/admin/dashboard"),
  });
  if (query.isLoading) return <LoadingState label="Calculando indicadores…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const data = query.data;
  const metrics = [
    { label: "Colaboradores", value: data.total_employees, icon: Users, note: "ativos na empresa" },
    {
      label: "Publicados",
      value: data.published_trainings,
      icon: BookOpen,
      note: "treinamentos disponíveis",
    },
    {
      label: "Atribuições",
      value: data.active_assignments,
      icon: ClipboardList,
      note: "entregas monitoradas",
    },
    {
      label: "Conclusão",
      value: `${data.completion_percent}%`,
      icon: CheckCircle2,
      note: "média da organização",
    },
  ];
  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Pulso de aprendizagem</span>
          <h1>Visão geral</h1>
          <p>Acompanhe a evolução da NovaTech em tempo real.</p>
        </div>
        <Link className="button primary" to="/admin/trainings/new">
          Novo treinamento
        </Link>
      </div>
      <div className="metric-grid">
        {metrics.map(({ label, value, icon: Icon, note }) => (
          <article key={label} className="metric-card">
            <span>
              <Icon size={18} />
            </span>
            <small>{label}</small>
            <strong>{value}</strong>
            <p>{note}</p>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="analytics-card">
          <div className="card-heading">
            <div>
              <span className="section-kicker">Engajamento</span>
              <h2>Progresso geral</h2>
            </div>
            <strong>{data.completion_percent}%</strong>
          </div>
          <div className="completion-chart">
            <div
              className="donut"
              style={{ "--progress": `${data.completion_percent * 3.6}deg` } as React.CSSProperties}
            >
              <span>{data.completion_percent}%</span>
            </div>
            <div>
              <p>
                <span className="legend-dot complete" /> Concluídas{" "}
                <strong>{data.completed_assignments}</strong>
              </p>
              <p>
                <span className="legend-dot pending" /> Pendentes{" "}
                <strong>{data.pending_assignments}</strong>
              </p>
            </div>
          </div>
        </section>
        <section className="recent-card">
          <div className="card-heading">
            <div>
              <span className="section-kicker">Conteúdo</span>
              <h2>Treinamentos recentes</h2>
            </div>
            <Link to="/admin/trainings">
              Ver todos <ArrowRight size={14} />
            </Link>
          </div>
          <div className="recent-list">
            {data.recent_trainings.map((training) => (
              <Link key={training.id} to={`/admin/trainings/${training.id}`}>
                <span className={`recent-icon type-${training.type.toLowerCase()}`}>
                  <BookOpen size={16} />
                </span>
                <div>
                  <strong>{training.title}</strong>
                  <small>
                    {trainingTypeLabel(training.type)} · {training.estimated_minutes} min
                  </small>
                </div>
                <span className={`status-${training.status.toLowerCase()}`}>
                  {publicationStatusLabel(training.status)}
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
