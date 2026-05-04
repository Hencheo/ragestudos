const API_URL = "http://localhost:8000";

async function safeFetch(url: string, options?: RequestInit) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`Erro na API: ${response.statusText}`);
    return await response.json();
  } catch (err) {
    console.warn(`⚠️ Backend offline em ${url}`);
    throw err;
  }
}

export async function queryHermes(question: string, subject?: string) {
  const formData = new FormData();
  formData.append("question", question);
  if (subject) formData.append("subject", subject);

  return safeFetch(`${API_URL}/query`, {
    method: "POST",
    body: formData,
  });
}

export async function uploadFiles(files: File[], subject: string) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("subject", subject);

  return safeFetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function getStats() {
  return safeFetch(`${API_URL}/stats`);
}

export async function clearDatabase() {
  return safeFetch(`${API_URL}/clear`, { method: "POST" });
}
