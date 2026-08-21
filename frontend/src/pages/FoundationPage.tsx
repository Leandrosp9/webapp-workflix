import { motion, useReducedMotion } from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  BrainCircuit,
  Cloud,
  Database,
  ShieldCheck,
  Workflow,
} from "lucide-react";

import { Brand } from "../components/Brand";
import { ServiceCard } from "../components/ServiceCard";
import { useSystemHealth } from "../features/system/useSystemHealth";

function FoundationPage() {
  const systemHealth = useSystemHealth();
  const reduceMotion = useReducedMotion();
  const backendState = systemHealth.isPending
    ? "checking"
    : systemHealth.isSuccess
      ? "online"
      : "offline";

  return (
    <div className="foundation-page">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />

      <header className="site-header">
        <Brand />
        <div className="phase-badge">
          <span className="phase-pulse" aria-hidden="true" />
          Foundation · v0.1.0
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="eyebrow">
              <span>Corporate Learning</span>
              <span className="eyebrow-separator" />
              <span>Knowledge Platform</span>
            </div>
            <h1 id="hero-title">
              Knowledge that moves
              <span>the whole company forward.</span>
            </h1>
            <p className="hero-copy">
              One secure place for training, procedures, progress, and source-aware intelligence —
              designed to turn scattered information into continuous learning.
            </p>
            <div className="hero-actions">
              <a className="primary-action" href="#platform-foundation">
                Explore the foundation
                <ArrowUpRight size={18} aria-hidden="true" />
              </a>
              <a className="secondary-action" href="http://localhost:8000/docs">
                API documentation
              </a>
            </div>
          </motion.div>

          <motion.div
            className="architecture-card"
            initial={reduceMotion ? false : { opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
            aria-label="Workflix architecture overview"
          >
            <div className="architecture-topline">
              <span>Platform architecture</span>
              <Activity size={16} aria-hidden="true" />
            </div>
            <div className="architecture-flow">
              <div className="architecture-node node-client">
                <Cloud size={20} aria-hidden="true" />
                <div>
                  <strong>Web client</strong>
                  <span>React · TypeScript</span>
                </div>
              </div>
              <span className="flow-line" aria-hidden="true" />
              <div className="architecture-node node-api">
                <Workflow size={20} aria-hidden="true" />
                <div>
                  <strong>Application API</strong>
                  <span>FastAPI · REST</span>
                </div>
              </div>
              <span className="flow-line" aria-hidden="true" />
              <div className="architecture-node node-data">
                <Database size={20} aria-hidden="true" />
                <div>
                  <strong>Knowledge core</strong>
                  <span>PostgreSQL · pgvector</span>
                </div>
              </div>
            </div>
            <div className="architecture-footer">
              <ShieldCheck size={17} aria-hidden="true" />
              Tenant-aware by design
              <span />
              <BrainCircuit size={17} aria-hidden="true" />
              Cloud AI ready
            </div>
          </motion.div>
        </section>

        <section className="foundation" id="platform-foundation" aria-labelledby="foundation-title">
          <div className="section-heading">
            <div>
              <span className="section-kicker">Live foundation</span>
              <h2 id="foundation-title">Built for operational confidence.</h2>
            </div>
            <p>
              The first product layer is running with versioned contracts, observable requests, and
              migration-owned infrastructure.
            </p>
          </div>

          <div className="service-grid">
            <ServiceCard
              icon={Cloud}
              label="Web experience"
              description="Responsive React shell with typed server state and accessible interaction states."
              meta="React · Vite · TanStack Query"
              state="online"
            />
            <ServiceCard
              icon={Workflow}
              label="Application API"
              description="Versioned FastAPI boundary with safe errors, OpenAPI, and correlation IDs."
              meta={systemHealth.data ? `API ${systemHealth.data.version}` : "FastAPI · SQLAlchemy"}
              state={backendState}
            />
            <ServiceCard
              icon={Database}
              label="Data platform"
              description="Migration-managed PostgreSQL foundation prepared for semantic retrieval."
              meta="PostgreSQL · Alembic · pgvector"
              state={systemHealth.isSuccess ? "online" : backendState}
            />
            <ServiceCard
              icon={ShieldCheck}
              label="Tenant security"
              description="Explicit company ownership model and backend-enforced isolation strategy."
              meta="RBAC · JWT · audit trail"
              state="planned"
            />
          </div>
        </section>
      </main>

      <footer>
        <Brand compact />
        <p>Workflix foundation · Designed for measurable corporate learning.</p>
        <span>2026</span>
      </footer>
    </div>
  );
}

export default FoundationPage;
