import type { PatentDetail, SearchMode, SearchResponse } from "../types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(
      typeof detail === "string" ? detail : "Ошибка сервера",
      res.status,
    );
  }
  return res.json() as Promise<T>;
}

export async function searchPatents(
  query: string,
  topK = 10,
  mode: SearchMode = "hybrid",
  live = true,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, mode, live }),
    signal,
  });
  return parseJson<SearchResponse>(res);
}

export async function getPatent(patentNumber: string): Promise<PatentDetail> {
  const res = await fetch(
    `${API_BASE}/api/v1/patents/${encodeURIComponent(patentNumber)}`,
  );
  return parseJson<PatentDetail>(res);
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
