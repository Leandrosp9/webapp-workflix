import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppProviders } from "./providers";

const FoundationPage = lazy(() => import("../pages/FoundationPage"));

function RouteFallback() {
  return (
    <main className="route-fallback" aria-busy="true" aria-label="Loading Workflix">
      <div className="brand-mark" aria-hidden="true">
        W
      </div>
      <span>Preparing your workspace…</span>
    </main>
  );
}

export function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<FoundationPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AppProviders>
  );
}
