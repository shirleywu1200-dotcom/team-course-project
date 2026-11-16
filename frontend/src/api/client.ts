// 11.2 通用 API client：保留既有認證與送出方式，解析統一錯誤格式。
// 規則：解析統一錯誤格式；收到 STALE_VERSION 由呼叫端重新載入，讓使用者重做，不自動重送。

const TOKEN_KEY = "g4.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? import.meta.env.VITE_API_TOKEN ?? "";
  } catch {
    return import.meta.env.VITE_API_TOKEN ?? "";
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // 無法存取 localStorage 時，只在本次工作階段有效
  }
}

function base(): string {
  return `${window.location.origin}/api/v1`;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH";
  body?: unknown;
  idempotencyKey?: string;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function nonEmptyString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() !== "" ? value : fallback;
}

function parseError(response: Response, data: unknown): ApiError {
  const error = asRecord(asRecord(data).error);
  return new ApiError(
    response.status,
    nonEmptyString(error.code, "HTTP_ERROR"),
    nonEmptyString(error.message, response.statusText || `HTTP ${response.status}`),
    asRecord(error.details),
  );
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${getToken()}` };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey;
  const res = await fetch(`${base()}${path}`, {
    method: opts.method ?? (opts.body === undefined ? "GET" : "POST"),
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    throw parseError(res, data);
  }
  return data as T;
}

export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
