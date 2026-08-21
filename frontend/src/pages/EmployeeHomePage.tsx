import { ArrowRight, Clock3, Flame, Play } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { TrainingCard } from "../components/TrainingCard";
import { useAuth } from "../features/auth/AuthProvider";
import { api } from "../services/http";
import type { EmployeeHome } from "../types/api";

export default function EmployeeHomePage() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["employee-home"],
    queryFn: () => api<EmployeeHome>("/employee/home"),
  });
  if (query.isLoading) return <LoadingState label="Preparando sua trilha…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const { featured, continue_learning: continuing, required, new: fresh, completed } = query.data;
  const firstName = user?.full_name.split(" ")[0];
  return (
    <div className="employee-home">
      <section className="welcome-row">
        <div>
          <span className="section-kicker">Seu espaço de aprendizagem</span>
          <h1>Olá, {firstName}. O que vamos aprender hoje?</h1>
        </div>
        <div className="streak-card">
          <Flame size={19} /> <strong>{completed.length}</strong>
          <span>concluídos</span>
        </div>
      </section>
      {featured ? (
        <section className="featured-training">
          <div className="featured-copy">
            <span className="featured-label">EM DESTAQUE PARA VOCÊ</span>
            <h2>{featured.title}</h2>
            <p>{featured.description}</p>
            <div className="featured-meta">
              <span>
                <Clock3 size={14} /> {featured.estimated_minutes} minutos
              </span>
              <span>{featured.type}</span>
            </div>
            <Link className="button primary" to={`/app/training/${featured.id}`}>
              <Play size={16} fill="currentColor" />{" "}
              {featured.progress_percent ? "Continuar" : "Começar agora"}
            </Link>
          </div>
          <div className="featured-visual">
            <div className="visual-ring ring-one" />
            <div className="visual-ring ring-two" />
            <Play size={38} fill="currentColor" />
          </div>
        </section>
      ) : (
        <section className="empty-hero">
          <h2>Você está em dia.</h2>
          <p>Novos treinamentos atribuídos aparecerão aqui.</p>
        </section>
      )}
      <TrainingSection title="Continue aprendendo" items={continuing} />
      <TrainingSection title="Obrigatórios" items={required} />
      <TrainingSection title="Novos para você" items={fresh} />
      {completed.length > 0 && <TrainingSection title="Concluídos" items={completed} />}
    </div>
  );
}

function TrainingSection({ title, items }: { title: string; items: EmployeeHome["new"] }) {
  if (!items.length) return null;
  return (
    <section className="training-section">
      <div className="section-title-row">
        <h2>{title}</h2>
        <Link to="/app/catalog">
          Ver todos <ArrowRight size={15} />
        </Link>
      </div>
      <div className="training-grid">
        {items.map((item) => (
          <TrainingCard key={item.id} training={item} />
        ))}
      </div>
    </section>
  );
}
