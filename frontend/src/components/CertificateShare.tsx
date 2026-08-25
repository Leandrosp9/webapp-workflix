import { Check, Copy, Linkedin, MessageCircle } from "lucide-react";
import { useState } from "react";

interface CertificateShareProps {
  code: string;
  title: string;
  companyName: string;
}

export function CertificateShare({ code, title, companyName }: CertificateShareProps) {
  const [copied, setCopied] = useState(false);
  const verificationUrl = `${window.location.origin}/verify/${encodeURIComponent(code)}`;
  const message = `Concluí “${title}” pela ${companyName} e recebi meu certificado Workflix. Confira a conquista:`;
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${message} ${verificationUrl}`)}`;
  const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(verificationUrl)}`;

  async function copyLink() {
    await navigator.clipboard.writeText(verificationUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2_000);
  }

  return (
    <div className="certificate-share" aria-label="Compartilhar conquista">
      <a
        className="share-button whatsapp"
        href={whatsappUrl}
        target="_blank"
        rel="noreferrer"
        aria-label="Compartilhar certificado no WhatsApp"
      >
        <MessageCircle size={15} /> WhatsApp
      </a>
      <a
        className="share-button linkedin"
        href={linkedInUrl}
        target="_blank"
        rel="noreferrer"
        aria-label="Compartilhar certificado no LinkedIn"
      >
        <Linkedin size={15} /> LinkedIn
      </a>
      <button className="share-button copy" type="button" onClick={() => void copyLink()}>
        {copied ? <Check size={15} /> : <Copy size={15} />}
        {copied ? "Copiado" : "Copiar link"}
      </button>
    </div>
  );
}
