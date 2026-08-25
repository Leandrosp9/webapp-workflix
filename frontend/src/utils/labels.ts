import type { LearningPathStatus, TrainingStatus, TrainingType } from "../types/api";

const trainingTypeLabels: Record<TrainingType, string> = {
  ARTICLE: "Artigo",
  VIDEO: "Vídeo",
  PDF: "PDF",
};

const publicationStatusLabels: Record<TrainingStatus | LearningPathStatus, string> = {
  DRAFT: "Rascunho",
  PUBLISHED: "Publicado",
};

export function trainingTypeLabel(type: TrainingType) {
  return trainingTypeLabels[type];
}

export function publicationStatusLabel(status: TrainingStatus | LearningPathStatus) {
  return publicationStatusLabels[status];
}
