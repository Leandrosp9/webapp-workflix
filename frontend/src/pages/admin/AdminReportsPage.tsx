import { Award, CheckCircle2, Clock3, Download, Route, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { ErrorState, LoadingState } from "../../components/PageState";
import { api, downloadFile } from "../../services/http";
import type { ManagerAnalytics } from "../../types/api";

export default function AdminReportsPage() {
  const query = useQuery({
    queryKey: ["manager-analytics"],
    queryFn: () => api<ManagerAnalytics>("/admin/analytics"),
  });
  if (query.isLoading) return <LoadingState label="Consolidando indicadores…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const { kpis } = query.data;
  return (
    <div>
      <div className="page-heading admin-heading">
        <div>
          <span className="section-kicker">Dados gerenciais</span>
          <h1>Relatórios e analytics</h1>
          <p>Indicadores calculados a partir de atribuições, progresso e certificados reais.</p>
        </div>
        <div className="report-actions">
          <button
            className="button secondary"
            type="button"
            onClick={() =>
              void downloadFile("/admin/reports/progress.csv", "workflix-progresso.csv")
            }
          >
            <Download size={15} /> Progresso CSV
          </button>
          <button
            className="button primary"
            type="button"
            onClick={() =>
              void downloadFile("/admin/reports/certificates.csv", "workflix-certificados.csv")
            }
          >
            <Download size={15} /> Certificados CSV
          </button>
        </div>
      </div>
      <div className="report-kpis">
        <Kpi icon={<Users />} label="Colaboradores" value={kpis.total_employees} />
        <Kpi icon={<CheckCircle2 />} label="Conclusão" value={`${kpis.completion_percent}%`} />
        <Kpi icon={<Clock3 />} label="Horas aprendidas" value={kpis.learning_hours} />
        <Kpi icon={<Award />} label="Certificados" value={kpis.certificates_issued} />
        <Kpi icon={<Route />} label="Trilhas publicadas" value={kpis.published_paths} />
      </div>
      <section className="report-section">
        <div className="card-heading">
          <h2>Desempenho por treinamento</h2>
          <strong>
            {kpis.completed_assignments}/{kpis.total_assignments}
          </strong>
        </div>
        <DataTable
          headers={["Treinamento", "Atribuídos", "Concluídos", "Conclusão", "Horas"]}
          rows={query.data.trainings.map((row) => [
            row.title,
            row.assignments,
            row.completed,
            `${row.completion_percent}%`,
            row.learning_hours,
          ])}
        />
      </section>
      <div className="report-split">
        <section className="report-section">
          <div className="card-heading">
            <h2>Trilhas</h2>
            <span>{kpis.overdue_assignments} atrasos</span>
          </div>
          <DataTable
            headers={["Trilha", "Atribuídos", "Certificados", "Conclusão"]}
            rows={query.data.paths.map((row) => [
              row.title,
              row.assignments,
              row.certificates,
              `${row.completion_percent}%`,
            ])}
          />
        </section>
        <section className="report-section">
          <div className="card-heading">
            <h2>Colaboradores</h2>
          </div>
          <DataTable
            headers={["Colaborador", "Progresso", "Horas", "Certificados"]}
            rows={query.data.employees.map((row) => [
              row.full_name,
              `${row.completion_percent}%`,
              row.learning_hours,
              row.certificates,
            ])}
          />
        </section>
      </div>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <article>
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: Array<Array<string | number>> }) {
  return (
    <div className="people-table-wrap">
      <table className="people-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index}>
                {row.map((cell, cellIndex) => (
                  <td key={`${index}-${cellIndex}`}>{cell}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={headers.length}>Ainda não há dados para este recorte.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
