import { ArrowRight, BookOpenCheck, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { AppLoadingScreen } from "../components/AppLoadingScreen";
import { Brand } from "../components/Brand";
import { useAuth } from "../features/auth/AuthProvider";
import { ApiError } from "../services/http";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("employee@workflix.demo");
  const [password, setPassword] = useState("Workflix@2026");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [transitioning, setTransitioning] = useState(false);

  if (transitioning) return <AppLoadingScreen label="Abrindo seu espaço Workflix…" />;
  if (user) return <Navigate to={user.role === "ADMIN" ? "/admin" : "/app"} replace />;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    setTransitioning(true);
    try {
      const current = await login(email, password);
      void navigate(current.role === "ADMIN" ? "/admin" : "/app", { replace: true });
    } catch (reason) {
      setTransitioning(false);
      setError(reason instanceof ApiError ? reason.message : "Não foi possível entrar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="login-story-inner">
          <Brand />
          <span className="eyebrow">
            <Sparkles size={14} /> aprendizagem que acontece
          </span>
          <h1>Conhecimento que transforma o trabalho.</h1>
          <p>
            Uma experiência contínua de aprendizagem para desenvolver pessoas, preservar
            conhecimento e acelerar resultados.
          </p>
          <div className="story-points">
            <span>
              <BookOpenCheck /> Conteúdo no ritmo de cada pessoa
            </span>
            <span>
              <ShieldCheck /> Ambiente seguro por empresa
            </span>
            <span>
              <CheckCircle2 /> Progresso e resultados visíveis
            </span>
          </div>
        </div>
        <div className="login-orbit orbit-one" />
        <div className="login-orbit orbit-two" />
      </section>
      <section className="login-panel">
        <form className="login-form" onSubmit={(event) => void submit(event)}>
          <div className="login-mobile-brand">
            <Brand />
          </div>
          <span className="form-kicker">Bem-vindo de volta</span>
          <h2>Acesse sua conta</h2>
          <p>Entre com as credenciais da sua empresa.</p>
          <label>
            E-mail corporativo
            <input
              type="email"
              value={email}
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <button className="button primary login-submit" type="submit" disabled={submitting}>
            {submitting ? "Entrando…" : "Entrar na Workflix"} <ArrowRight size={17} />
          </button>
          <div className="demo-accounts">
            <strong>Acesso de demonstração</strong>
            <button type="button" onClick={() => setEmail("employee@workflix.demo")}>
              Colaborador
            </button>
            <button type="button" onClick={() => setEmail("admin@workflix.demo")}>
              Administrador
            </button>
          </div>
          <small>Ambiente protegido · Seus dados permanecem na sua empresa</small>
        </form>
      </section>
    </main>
  );
}
