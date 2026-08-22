import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";

import { ErrorState, LoadingState } from "../components/PageState";
import { TrainingCard } from "../components/TrainingCard";
import { api } from "../services/http";
import type { Training } from "../types/api";

export default function CatalogPage() {
  const query = useQuery({
    queryKey: ["employee-trainings"],
    queryFn: () => api<Training[]>("/employee/trainings"),
  });
  if (query.isLoading) return <LoadingState />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="section-kicker">Biblioteca pessoal</span>
          <h1>Meus treinamentos</h1>
          <p>Todo o conteúdo atribuído a você, em um só lugar.</p>
        </div>
      </div>
      {query.data.length === 0 ? (
        <div className="empty-hero">
          <BookOpen />
          <h2>Seu catálogo está pronto para receber conteúdo.</h2>
          <p>Os treinamentos atribuídos pela empresa aparecerão aqui.</p>
        </div>
      ) : (
        <div className="training-grid wide">
          {query.data.map((item) => (
            <TrainingCard key={item.id} training={item} />
          ))}
        </div>
      )}
    </div>
  );
}
