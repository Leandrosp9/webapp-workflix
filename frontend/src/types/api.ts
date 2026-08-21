export type Role = "ADMIN" | "EMPLOYEE";
export type TrainingType = "ARTICLE" | "VIDEO" | "PDF";
export type TrainingStatus = "DRAFT" | "PUBLISHED";
export type DocumentStatus =
  "UPLOADED" | "EXTRACTING" | "EXTRACTED" | "INDEXING" | "READY" | "FAILED";

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  status: DocumentStatus;
  page_count: number;
  chunk_count: number;
  error_code: string | null;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

export interface User {
  id: string;
  company_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface UserSummary extends User {
  assigned: number;
  completed: number;
  pending: number;
  completion_percent: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Training {
  id: string;
  company_id: string;
  title: string;
  description: string;
  type: TrainingType;
  thumbnail_url: string | null;
  content: string;
  video_url: string | null;
  has_pdf: boolean;
  estimated_minutes: number;
  status: TrainingStatus;
  created_at: string;
  updated_at: string;
  progress_percent: number | null;
  assigned_at: string | null;
  due_date: string | null;
  has_quiz: boolean;
  document_version?: DocumentVersion | null;
}

export interface RagSource {
  document_id: string;
  document_version_id: string;
  title: string;
  page: number;
  excerpt: string;
  score: number;
}

export interface RagAnswer {
  answer: string;
  sources: RagSource[];
  provider: string;
  model: string;
}

export interface EmployeeHome {
  featured: Training | null;
  continue_learning: Training[];
  required: Training[];
  new: Training[];
  completed: Training[];
}

export interface Dashboard {
  total_employees: number;
  published_trainings: number;
  active_assignments: number;
  completion_percent: number;
  completed_assignments: number;
  pending_assignments: number;
  recent_trainings: Training[];
}

export interface QuizOption {
  id: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  text: string;
  options: QuizOption[];
}

export interface Quiz {
  id: string;
  training_id: string;
  passing_score: number;
  questions: QuizQuestion[];
}

export interface QuizResult {
  id: string;
  score: number;
  correct_answers: number;
  total_questions: number;
  passed: boolean;
  completed_at: string;
  answers: Array<{
    question_id: string;
    selected_option_id: string;
    correct_option_id: string;
    is_correct: boolean;
    explanation: string;
  }>;
}
