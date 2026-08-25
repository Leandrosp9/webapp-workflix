import { Award, CalendarDays, CheckCircle2, Clock3, ShieldCheck, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Brand } from "../components/Brand";
import { CertificateShare } from "../components/CertificateShare";
import { ErrorState, LoadingState } from "../components/PageState";
import { api } from "../services/http";
import type { CertificateVerification } from "../types/api";

export default function VerifyCertificatePage() {
  const { code = "" } = useParams();
  const query = useQuery({
    queryKey: ["certificate-verification", code],
    queryFn: () => api<CertificateVerification>(`/certificates/verify/${encodeURIComponent(code)}`),
    retry: false,
  });

  return (
    <main className="verification-page">
      <header className="verification-header">
        <Brand />
        <Link to="/login">Acessar plataforma</Link>
      </header>
      {query.isLoading ? (
        <LoadingState label="Validando certificado…" />
      ) : !query.data ? (
        <section className="verification-panel">
          <ErrorState retry={() => void query.refetch()} />
        </section>
      ) : (
        <section className="verification-panel certificate-valid">
          <div className="verification-seal" aria-hidden="true">
            <Award />
          </div>
          <span className="verification-status">
            <CheckCircle2 size={16} /> Certificado autêntico
          </span>
          <span className="section-kicker">
            {query.data.certificate_type === "TRAINING"
              ? "Conclusão de treinamento"
              : "Conclusão de trilha"}
          </span>
          <h1>{query.data.title}</h1>
          <p className="verification-intro">Emitido pela {query.data.company_name} para</p>
          <h2>{query.data.user_full_name}</h2>
          <div className="verification-details">
            {query.data.user_cpf_masked && (
              <span>
                <UserRound /> CPF {query.data.user_cpf_masked}
              </span>
            )}
            <span>
              <Clock3 /> {formatWorkload(query.data.workload_minutes)}
            </span>
            <span>
              <CalendarDays /> Emitido em {formatDate(query.data.issued_at)}
            </span>
          </div>
          <div className="certificate-code verification-code">
            <ShieldCheck size={17} /> {query.data.code}
          </div>
          <CertificateShare
            code={query.data.code}
            title={query.data.title}
            companyName={query.data.company_name}
          />
          <p className="verification-privacy">
            A verificação pública protege os dados pessoais e exibe o CPF de forma mascarada.
          </p>
        </section>
      )}
    </main>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

function formatWorkload(minutes: number) {
  if (minutes < 60) return `${minutes} minutos`;
  const hours = minutes / 60;
  return `${hours.toLocaleString("pt-BR")} hora${hours === 1 ? "" : "s"}`;
}
