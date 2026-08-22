import { Award, Download, ShieldCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "../components/PageState";
import { ApiError, downloadFile, api } from "../services/http";
import type { Certificate } from "../types/api";

export default function CertificatesPage() {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const query = useQuery({
    queryKey: ["employee-certificates"],
    queryFn: () => api<Certificate[]>("/employee/certificates"),
  });
  if (query.isLoading) return <LoadingState label="Buscando suas conquistas…" />;
  if (!query.data) return <ErrorState retry={() => void query.refetch()} />;

  async function downloadCertificate(certificate: Certificate) {
    setDownloadError("");
    setDownloadingId(certificate.id);
    try {
      await downloadFile(
        `/certificates/${certificate.id}/pdf`,
        `workflix-${certificate.learning_path_title}.pdf`,
      );
    } catch (reason) {
      setDownloadError(
        reason instanceof ApiError ? reason.message : "Não foi possível baixar o certificado.",
      );
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="section-kicker">Conquistas verificáveis</span>
          <h1>Certificados</h1>
          <p>Baixe os certificados emitidos ao concluir suas trilhas.</p>
        </div>
      </div>
      {downloadError && (
        <div className="form-error global-message" role="alert">
          {downloadError}
        </div>
      )}
      {query.data.length === 0 ? (
        <div className="empty-hero">
          <Award />
          <h2>Sua próxima conquista começa agora.</h2>
          <p>Conclua uma trilha obrigatória para receber o certificado.</p>
        </div>
      ) : (
        <div className="certificate-grid">
          {query.data.map((certificate) => (
            <article className="certificate-card" key={certificate.id}>
              <div className="certificate-ribbon">
                <Award />
              </div>
              <span className="section-kicker">Certificado de conclusão</span>
              <h2>{certificate.learning_path_title}</h2>
              <p>
                Emitido por {certificate.company_name} em {formatDate(certificate.issued_at)}.
              </p>
              <div className="certificate-code">
                <ShieldCheck size={15} /> {certificate.code}
              </div>
              <button
                className="button primary"
                type="button"
                disabled={downloadingId === certificate.id}
                onClick={() => void downloadCertificate(certificate)}
              >
                <Download size={15} />
                {downloadingId === certificate.id ? "Preparando PDF…" : "Baixar PDF"}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}
