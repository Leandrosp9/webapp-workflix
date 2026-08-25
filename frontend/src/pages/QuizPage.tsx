import { ArrowLeft, ArrowRight, CheckCircle2, RotateCcw, Trophy, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/PageState";
import { api } from "../services/http";
import type { Quiz, QuizResult } from "../types/api";

export default function QuizPage() {
  const { trainingId = "" } = useParams();
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const query = useQuery({
    queryKey: ["quiz", trainingId],
    queryFn: () => api<Quiz>(`/employee/trainings/${trainingId}/quiz`),
  });
  const submit = useMutation({
    mutationFn: (quiz: Quiz) =>
      api<QuizResult>(`/employee/trainings/${trainingId}/quiz/attempts`, {
        method: "POST",
        body: JSON.stringify({
          answers: quiz.questions.map((question) => ({
            question_id: question.id,
            option_id: answers[question.id],
          })),
        }),
      }),
    onSuccess: (result) => {
      if (result.passed) {
        void queryClient.invalidateQueries({ queryKey: ["employee-home"] });
        void queryClient.invalidateQueries({ queryKey: ["employee-certificates"] });
      }
    },
  });
  const answered = useMemo(() => Object.keys(answers).length, [answers]);
  if (query.isLoading) return <LoadingState label="Preparando avaliação…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;
  const quiz = query.data;
  if (submit.data) {
    const result = submit.data;
    return (
      <div className="result-page">
        <div className={`result-icon ${result.passed ? "passed" : "failed"}`}>
          {result.passed ? <Trophy /> : <RotateCcw />}
        </div>
        <span className="section-kicker">Resultado da avaliação</span>
        <h1>{result.passed ? "Muito bem!" : "Vamos tentar mais uma vez?"}</h1>
        <div className="score-ring">
          <strong>{result.score}</strong>
          <span>/ 100</span>
        </div>
        <p>
          Você acertou {result.correct_answers} de {result.total_questions} questões.
        </p>
        <div className="result-review">
          {result.answers.map((answer, answerIndex) => (
            <div key={answer.question_id} className={answer.is_correct ? "correct" : "incorrect"}>
              {answer.is_correct ? <CheckCircle2 /> : <XCircle />}
              <span>
                <strong>Questão {answerIndex + 1}</strong>
                {answer.explanation}
              </span>
            </div>
          ))}
        </div>
        <div className="result-actions">
          {!result.passed && (
            <button className="button secondary" onClick={() => submit.reset()}>
              Tentar novamente
            </button>
          )}
          <Link
            className="button primary"
            to={result.passed ? "/app/certificates" : `/app/training/${trainingId}`}
          >
            {result.passed ? "Ver certificado" : "Voltar ao treinamento"}
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    );
  }
  const question = quiz.questions[index];
  const isLast = index === quiz.questions.length - 1;
  return (
    <div className="quiz-page">
      <Link className="back-link" to={`/app/training/${trainingId}`}>
        <ArrowLeft size={16} /> Sair da avaliação
      </Link>
      <div className="quiz-progress-row">
        <span>
          Questão {index + 1} de {quiz.questions.length}
        </span>
        <span>{answered} respondidas</span>
      </div>
      <div className="quiz-progress">
        <span style={{ width: `${((index + 1) / quiz.questions.length) * 100}%` }} />
      </div>
      <section className="quiz-card">
        <span className="question-number">{String(index + 1).padStart(2, "0")}</span>
        <h1>{question.text}</h1>
        <div className="quiz-options">
          {question.options.map((option, optionIndex) => (
            <button
              key={option.id}
              type="button"
              className={answers[question.id] === option.id ? "selected" : ""}
              onClick={() => setAnswers((current) => ({ ...current, [question.id]: option.id }))}
            >
              <span>{String.fromCharCode(65 + optionIndex)}</span>
              {option.text}
            </button>
          ))}
        </div>
        <div className="quiz-actions">
          <button
            className="button ghost"
            type="button"
            disabled={index === 0}
            onClick={() => setIndex(index - 1)}
          >
            Anterior
          </button>
          {isLast ? (
            <button
              className="button primary"
              type="button"
              disabled={answered !== quiz.questions.length || submit.isPending}
              onClick={() => submit.mutate(quiz)}
            >
              {submit.isPending ? "Corrigindo…" : "Finalizar avaliação"}
            </button>
          ) : (
            <button
              className="button primary"
              type="button"
              disabled={!answers[question.id]}
              onClick={() => setIndex(index + 1)}
            >
              Próxima <ArrowRight size={16} />
            </button>
          )}
        </div>
        {submit.isError && (
          <div className="form-error">Não foi possível corrigir. Revise as respostas.</div>
        )}
      </section>
    </div>
  );
}
