export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export class HTTPError extends Error {
  constructor(public status: number) { super(status === 401 || status === 403 ? "API key expired or invalid. Enter a current key." : `Request failed (${status}).`); }
}
export async function api<T>(path: string, key: string, signal?: AbortSignal, body?: unknown): Promise<T> {
  const response = await fetch(API + path, {method: body === undefined ? "GET" : "POST", signal,
    headers: {...(key ? {Authorization: `Bearer ${key}`} : {}), ...(body === undefined ? {} : {"Content-Type": "application/json"})},
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store", credentials: "omit"});
  if (!response.ok) throw new HTTPError(response.status);
  return response.json();
}
