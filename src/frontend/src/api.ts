export const API_BASE: string = import.meta.env.DEV
  ? import.meta.env.VITE_API_BASE ?? "http://localhost:30007"
  : "https://backend.ifamished.com";
export const MAX_VIDEO_BYTES = 50 * 1024 * 1024;
const TOKEN_KEY = "FILLER.token";

export type Skills = Record<string, number>;
export interface Developer { id: number; login: string; name: string; avatar_url: string | null; skills: Skills; interests: string[] }
export interface Project {
  id: number; title: string; description: string | null; repo_url: string; video_url: string | null;
  needs: Skills; tags: string[]; maintainer_id: number;
}
export interface FeedProject extends Project { match_score: number; skill_fit: number; interest_fit: number }
export interface RepoInfo { repo_url: string; title: string; description: string | null; needs: Skills; tags: string[]; stars: number }
export type SwipeAction = "LIKE" | "SKIP" | "APPLY";
export type ProjectInput = Omit<Project, "id" | "maintainer_id">;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const getToken = (): string | null => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (t: string | null): void => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ }
};

export async function api<T = void>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try { res = await fetch(API_BASE + path, { ...init, headers }); }
  catch { throw new ApiError(0, "Can't reach the server. Check that the API is running."); }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : body.detail?.[0]?.msg ?? detail;
    } catch { /* keep statusText */ }
    if (res.status === 401) window.dispatchEvent(new Event("FILLER:unauthorized"));
    throw new ApiError(res.status, detail.replace(/^Value error, /, ""));
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

/** Only http(s) links are rendered, so a stored "javascript:" URL can't run. */
export function safeUrl(raw: string | null): string | null {
  if (!raw) return null;
  try { const u = new URL(raw); return u.protocol === "http:" || u.protocol === "https:" ? u.href : null; }
  catch { return null; }
}
