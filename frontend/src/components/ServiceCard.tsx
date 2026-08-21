import type { LucideIcon } from "lucide-react";

interface ServiceCardProps {
  description: string;
  icon: LucideIcon;
  label: string;
  meta: string;
  state: "online" | "checking" | "planned" | "offline";
}

const stateLabels: Record<ServiceCardProps["state"], string> = {
  online: "Online",
  checking: "Checking",
  planned: "Planned",
  offline: "Unavailable",
};

export function ServiceCard({ description, icon: Icon, label, meta, state }: ServiceCardProps) {
  return (
    <article className="service-card">
      <div className="service-card-head">
        <span className="service-icon" aria-hidden="true">
          <Icon size={19} strokeWidth={1.8} />
        </span>
        <span className={`status-pill status-${state}`}>
          <span className="status-dot" aria-hidden="true" />
          {stateLabels[state]}
        </span>
      </div>
      <h3>{label}</h3>
      <p>{description}</p>
      <span className="service-meta">{meta}</span>
    </article>
  );
}
