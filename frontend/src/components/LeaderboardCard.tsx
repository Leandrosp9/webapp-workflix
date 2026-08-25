import { Medal, Trophy } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../services/http";
import type { Leaderboard } from "../types/api";
import { UserAvatar } from "./UserAvatar";

export function LeaderboardCard() {
  const query = useQuery({
    queryKey: ["employee-leaderboard"],
    queryFn: () => api<Leaderboard>("/employee/leaderboard"),
  });

  if (query.isLoading) {
    return <div className="leaderboard-card leaderboard-loading" aria-label="Carregando ranking" />;
  }
  if (!query.data) return null;

  return (
    <section className="leaderboard-card" aria-labelledby="leaderboard-title">
      <div className="leaderboard-heading">
        <div>
          <span className="section-kicker">Aprendizado em movimento</span>
          <h2 id="leaderboard-title">Ranking da equipe</h2>
        </div>
        <span className="leaderboard-trophy" aria-hidden="true">
          <Trophy />
        </span>
      </div>
      <div className="leaderboard-current">
        <span>Sua posição</span>
        <strong>#{query.data.current_user.rank}</strong>
        <small>
          {query.data.current_user.completed_trainings} concluídos ·{" "}
          {query.data.current_user.average_progress}% de progresso médio
        </small>
      </div>
      <ol className="leaderboard-list">
        {query.data.entries.slice(0, 5).map((entry) => (
          <li className={entry.is_current_user ? "is-current" : ""} key={entry.user_id}>
            <span className={`rank-number rank-${entry.rank}`}>
              {entry.rank <= 3 ? <Medal size={16} /> : entry.rank}
            </span>
            <UserAvatar
              userId={entry.user_id}
              fullName={entry.full_name}
              hasAvatar={entry.has_avatar}
              avatarUpdatedAt={entry.avatar_updated_at}
            />
            <span className="leaderboard-person">
              <strong>
                {entry.full_name} {entry.is_current_user && <em>Você</em>}
              </strong>
              <small>{entry.completed_trainings} treinamentos concluídos</small>
            </span>
            <strong className="leaderboard-progress">{entry.average_progress}%</strong>
          </li>
        ))}
      </ol>
      <p className="leaderboard-note">Critério: conclusões e progresso médio nos treinamentos.</p>
    </section>
  );
}
