import { ArrowRight, Clock3, Flame, Play, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { LeaderboardCard } from "../components/LeaderboardCard";
import { TrainingCard } from "../components/TrainingCard";
import { useAuth } from "../features/auth/AuthProvider";
import { api } from "../services/http";
import type { EmployeeHome } from "../types/api";
import { trainingTypeLabel } from "../utils/labels";

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
  const motivation = motivationalMessage(continuing, completed.length);
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
      <section className="motivation-banner">
        <span className="motivation-icon" aria-hidden="true">
          <Sparkles />
        </span>
        <div>
          <span className="section-kicker">Impulso do dia</span>
          <strong>{motivation.title}</strong>
          <p>{motivation.copy}</p>
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
              <span>{trainingTypeLabel(featured.type)}</span>
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
      <LeaderboardCard />
      <TrainingSection title="Continue aprendendo" items={continuing} />
      <TrainingSection title="Obrigatórios" items={required} />
      <TrainingSection title="Novos para você" items={fresh} />
      {completed.length > 0 && <TrainingSection title="Concluídos" items={completed} />}
    </div>
  );
}

function motivationalMessage(continuing: EmployeeHome["continue_learning"], completed: number) {
  const closest = [...continuing].sort(
    (first, second) => (second.progress_percent ?? 0) - (first.progress_percent ?? 0),
  )[0];
  if ((closest?.progress_percent ?? 0) >= 75) {
    return {
      title: "Você está na reta final.",
      copy: `Mais um passo em “${closest.title}” e uma nova conquista entra para o seu histórico.`,
    };
  }
  if (completed >= 3) {
    return {
      title: "Consistência transforma conhecimento em resultado.",
      copy: `Você já concluiu ${completed} treinamentos. Continue construindo esse ritmo.`,
    };
  }
  if (closest) {
    return {
      title: "Progresso também se faz em pequenos passos.",
      copy: `Reserve alguns minutos para continuar “${closest.title}” hoje.`,
    };
  }
  return {
    title: "Toda conquista começa com curiosidade.",
    copy: "Escolha um conteúdo do catálogo e dê o próximo passo no seu desenvolvimento.",
  };
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
