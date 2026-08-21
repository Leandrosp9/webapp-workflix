import type { TokenResponse } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const ACCESS_KEY = "workflix.access";
const REFRESH_KEY = "workflix.refresh";

interface ErrorEnvelope {
  error?: { message?: string; request_id?: string };
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const sessionTokens = {
  access: () => localStorage.getItem(ACCESS_KEY),
  refresh: () => localStorage.getItem(REFRESH_KEY),
  save: (tokens: Pick<TokenResponse, "access_token" | "refresh_token">) => {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function errorFrom(response: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope = {};
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    // A proxy or network edge can return a non-JSON error document.
  }
  return new ApiError(
    envelope.error?.message ?? "Não foi possível concluir esta operação.",
    response.status,
    envelope.error?.request_id ?? response.headers.get("X-Request-ID") ?? undefined,
  );
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = sessionTokens.refresh();
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    sessionTokens.clear();
    return false;
  }
  sessionTokens.save((await response.json()) as TokenResponse);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const accessToken = sessionTokens.access();
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Não foi possível conectar ao servidor.", 0);
  }
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return api<T>(path, init, false);
  }
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getJson(path: string): Promise<unknown> {
  return api<unknown>(path);
}

export function loginRequest(email: string, password: string): Promise<TokenResponse> {
  return api<TokenResponse>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    false,
  );
}

export async function downloadPdf(trainingId: string, retry = true): Promise<void> {
  const headers = new Headers();
  const accessToken = sessionTokens.access();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}/trainings/${trainingId}/pdf`, { headers });
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return downloadPdf(trainingId, false);
  }
  if (!response.ok) throw await errorFrom(response);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `workflix-${trainingId}.pdf`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
