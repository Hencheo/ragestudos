/**
 * API Client do Hermes RAG Engine.
 * 
 * Inclui:
 * - Retry automático (2 tentativas) para erros transitórios
 * - Timeout padrão de 60s
 * - Tratamento de rate limiting (429)
 * - Cache-busting para requests GET
 */

const API_URL = "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 60000;
const MAX_RETRIES = 2;

class ApiError extends Error {
  status: number;
  isRateLimit: boolean;
  isServerError: boolean;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.isRateLimit = status === 429;
    this.isServerError = status >= 500;
  }
}

async function safeFetch(
  url: string,
  options?: RequestInit,
  retries: number = MAX_RETRIES
): Promise<any> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  const fetchOptions: RequestInit = {
    ...options,
    signal: controller.signal,
  };

  try {
    const response = await fetch(url, fetchOptions);

    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      const waitMs = retryAfter ? parseInt(retryAfter) * 1000 : 5000;

      if (retries > 0) {
        console.warn(`⏳ Rate limited. Aguardando ${waitMs}ms antes de retry...`);
        await new Promise((r) => setTimeout(r, waitMs));
        return safeFetch(url, options, retries - 1);
      }
      throw new ApiError("Limite de requisições excedido. Aguarde um momento.", 429);
    }

    if (!response.ok) {
      const errorBody = await response.text().catch(() => "");
      const detail = errorBody ? `: ${errorBody}` : "";

      // Retry em erros de servidor (5xx)
      if (response.status >= 500 && retries > 0) {
        console.warn(`🔄 Erro ${response.status}, tentando novamente...`);
        await new Promise((r) => setTimeout(r, 1000));
        return safeFetch(url, options, retries - 1);
      }

      throw new ApiError(`Erro na API (${response.status})${detail}`, response.status);
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;

    // Retry em erros de rede
    if (retries > 0 && (err.name === "AbortError" || err.message?.includes("fetch"))) {
      console.warn("🔄 Erro de conexão, tentando novamente...");
      await new Promise((r) => setTimeout(r, 1000));
      return safeFetch(url, options, retries - 1);
    }

    console.warn(`⚠️ Backend offline em ${url}`);
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export async function queryHermes(question: string, subject?: string, sessionId: string = "default") {
  const formData = new FormData();
  formData.append("question", question);
  if (subject) formData.append("subject", subject);
  formData.append("session_id", sessionId);

  return safeFetch(`${API_URL}/query`, {
    method: "POST",
    body: formData,
  });
}

export async function uploadFiles(files: File[], subject: string, useOcr: boolean = true) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("subject", subject);
  formData.append("use_ocr", String(useOcr));

  return safeFetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function fetchExternalProcess(processNumber: string) {
  const formData = new FormData();
  formData.append("process_number", processNumber);

  return safeFetch(`${API_URL}/external/fetch-process`, {
    method: "POST",
    body: formData,
  });
}

export async function getStats() {
  return safeFetch(`${API_URL}/stats`);
}

export async function getSessions() {
  return safeFetch(`${API_URL}/sessions`);
}

export async function getSessionMessages(sessionId: string) {
  return safeFetch(`${API_URL}/sessions/${encodeURIComponent(sessionId)}/messages`);
}

export async function clearDatabase(options?: { session_id?: string }) {
  const formData = new FormData();
  if (options?.session_id) {
    formData.append("session_id", options.session_id);
  }
  return safeFetch(`${API_URL}/clear`, { method: "POST", body: formData });
}

export async function getUploadStatus(taskId: string) {
  return safeFetch(`${API_URL}/upload/status/${encodeURIComponent(taskId)}`);
}

export async function cancelUpload(taskId: string) {
  return safeFetch(`${API_URL}/upload/cancel/${encodeURIComponent(taskId)}`, { method: "POST" });
}

export async function getHealth() {
  return safeFetch(`${API_URL}/health`);
}

export async function getMetrics() {
  return safeFetch(`${API_URL}/metrics`);
}

export async function deleteDocument(fileName: string) {
  return safeFetch(`${API_URL}/documents/${encodeURIComponent(fileName)}`, { method: "DELETE" });
}

export async function getConfig() {
  return safeFetch(`${API_URL}/config`);
}

export async function updateConfig(provider: string, model: string) {
  const formData = new FormData();
  formData.append("llm_provider", provider);
  formData.append("model_name", model);
  return safeFetch(`${API_URL}/config`, { method: "POST", body: formData });
}
