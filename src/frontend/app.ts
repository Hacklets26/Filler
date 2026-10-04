// ---------- Config ----------
const API_BASE = "http://ashburn.hungernet.dev:30007";
const MAX_VIDEO_BYTES = 50 * 1024 * 1024;
const STORE_KEY = "patchwork.developerId";
const LEVELS = [1, 2, 3, 4, 5];

// ---------- Types (mirror the backend README) ----------
type Skills = Record<string, number>;
type SwipeAction = "LIKE" | "SKIP" | "APPLY";

interface Developer {
  id: number;
  name: string;
  skills: Skills;
  interests: string[];
  swipe_history: number[];
}

interface Project {
  id: number;
  title: string;
  repo_url: string;
  video_url: string | null;
  needs: Skills;
  tags: string[];
  maintainer_id: number;
  match_score?: number; // only present on /feed results
}

// ---------- API client ----------
class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_BASE + path, init);
  } catch {
    throw new ApiError(0, "Can't reach the server. Check it is running, and that this page isn't on https while the API is on http.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const send = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---------- State ----------
let developer: Developer | null = null;
let feed: Project[] = [];
let allProjects: Project[] = [];
let applied = new Set<number>();
const skillsDraft: Skills = {};
const interestsDraft = new Set<string>();
const needsDraft: Skills = {};

// ---------- Helpers ----------
const normalize = (s: string): string => s.trim().toLowerCase();

function $<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing element #${id}`);
  return node as T;
}

// textContent only, so user text is never parsed as HTML
function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<HTMLElementTagNameMap[K]> = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

/** Only allow http(s) links so a saved "javascript:" URL can't run. */
function safeUrl(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
  } catch { return null; }
}

function setStatus(msg: string, bad = false): void {
  const box = $("status");
  box.textContent = msg;
  box.hidden = !msg;
  box.className = bad ? "status bad" : "status";
}

const fail = (e: unknown): void => setStatus(e instanceof Error ? e.message : "Something went wrong.", true);

function storage(op: () => void): void { try { op(); } catch { /* storage may be blocked */ } }
const appliedKey = (id: number): string => `patchwork.applied.${id}`;

// ---------- Rendering ----------
function renderChips(target: HTMLElement, entries: { label: string; onRemove: () => void }[]): void {
  target.replaceChildren(...entries.map(({ label, onRemove }) =>
    el("li", { className: "chip" }, label,
      el("button", { type: "button", ariaLabel: `Remove ${label}`, textContent: "×", onclick: onRemove }))));
}

function renderDrafts(): void {
  renderChips($("skill-list"), Object.entries(skillsDraft).map(([k, v]) => ({
    label: `${k} ${v}`, onRemove: () => { delete skillsDraft[k]; renderDrafts(); },
  })));
  renderChips($("interest-list"), [...interestsDraft].map((k) => ({
    label: k, onRemove: () => { interestsDraft.delete(k); renderDrafts(); },
  })));
  renderChips($("need-list"), Object.entries(needsDraft).map(([k, v]) => ({
    label: `${k} ${v}`, onRemove: () => { delete needsDraft[k]; renderDrafts(); },
  })));
}

function renderProject(p: Project): HTMLElement {
  const mySkills = developer?.skills ?? {};
  const myInterests = new Set((developer?.interests ?? []).map(normalize));

  const head = el("div", { className: "post-head" }, el("strong", {}, p.title));
  if (p.match_score !== undefined) {
    head.append(el("span", { className: "score" }, `${Math.round(p.match_score * 100)}% match`));
  }
  const card = el("li", { className: "post" }, head);

  const repo = safeUrl(p.repo_url);
  if (repo) card.append(el("p", {}, el("a", { href: repo, target: "_blank", rel: "noopener noreferrer" }, "View repository")));

  const video = safeUrl(p.video_url);
  if (video) card.append(el("video", { src: video, controls: true, preload: "metadata" }));

  const needs = Object.entries(p.needs ?? {}).map(([skill, level]) =>
    el("li", { className: (mySkills[skill] ?? 0) >= level ? "chip shared" : "chip" }, `${skill} ${level}`));
  const tags = (p.tags ?? []).map((t) =>
    el("li", { className: myInterests.has(normalize(t)) ? "chip shared" : "chip" }, t));
  if (needs.length || tags.length) card.append(el("ul", { className: "chips" }, ...needs, ...tags));

  if (developer) {
    const act = (action: SwipeAction, label: string, secondary: boolean) =>
      el("button", { type: "button", textContent: label, className: secondary ? "secondary" : "", onclick: () => swipe(p, action) });
    card.append(el("div", { className: "actions" }, act("SKIP", "Skip", true), act("LIKE", "Like", true), act("APPLY", "Apply", false)));
  }
  return card;
}

function renderApplied(): void {
  const mine = allProjects.filter((p) => applied.has(p.id));
  $("match-list").replaceChildren(...(mine.length
    ? mine.map((p) => {
        const repo = safeUrl(p.repo_url);
        return el("li", { className: "match" },
          el("h3", {}, p.title),
          repo ? el("p", {}, el("a", { href: repo, target: "_blank", rel: "noopener noreferrer" }, "Open repository")) : el("p", {}, "No repository link"));
      })
    : [el("li", { className: "empty" }, "Projects you apply to will show up here.")]));
}

function renderFeed(): void {
  const list = developer ? feed : allProjects;
  $("feed-list").replaceChildren(...(list.length
    ? list.map(renderProject)
    : [el("li", { className: "empty" }, developer ? "You've seen every project. Check back soon." : "No projects yet. Pitch the first one.")]));
  renderApplied();
}

// ---------- Data flow ----------
async function refresh(): Promise<void> {
  try {
    const [projects, ranked] = await Promise.all([
      api<Project[]>("/projects"),
      developer ? api<Project[]>(`/feed/${developer.id}`) : Promise.resolve([] as Project[]),
    ]);
    allProjects = projects;
    feed = ranked;
    renderFeed();
  } catch (e) { fail(e); }
}

function adoptDeveloper(d: Developer): void {
  developer = d;
  $<HTMLInputElement>("dev-name").value = d.name;
  Object.keys(skillsDraft).forEach((k) => delete skillsDraft[k]);
  Object.assign(skillsDraft, d.skills);
  interestsDraft.clear();
  d.interests.forEach((i) => interestsDraft.add(i));
  storage(() => localStorage.setItem(STORE_KEY, String(d.id)));
  storage(() => {
    const saved = localStorage.getItem(appliedKey(d.id));
    applied = new Set<number>(saved ? (JSON.parse(saved) as number[]) : []);
  });
  renderDrafts();
}

async function saveProfile(): Promise<void> {
  const name = $<HTMLInputElement>("dev-name").value.trim();
  if (!name) return setStatus("Enter your name before saving.", true);
  const body = { name, skills: { ...skillsDraft }, interests: [...interestsDraft] };
  try {
    const d = developer
      ? await api<Developer>(`/developer/${developer.id}`, send("PUT", body))
      : await api<Developer>("/developer", send("POST", body));
    adoptDeveloper(d);
    setStatus("Profile saved.");
    await refresh();
  } catch (e) { fail(e); }
}

async function swipe(p: Project, action: SwipeAction): Promise<void> {
  if (!developer) return;
  try {
    await api("/swipe", send("POST", { developer_id: developer.id, project_id: p.id, action }));
    if (action === "APPLY") {
      applied.add(p.id);
      const id = developer.id;
      storage(() => localStorage.setItem(appliedKey(id), JSON.stringify([...applied])));
      setStatus(`Applied to ${p.title}.`);
    } else {
      setStatus("");
    }
    developer.swipe_history.push(p.id);
    await refresh();
  } catch (e) {
    fail(e instanceof ApiError && e.status === 409 ? new Error("You already responded to this project.") : e);
  }
}

async function onPitch(e: SubmitEvent): Promise<void> {
  e.preventDefault();
  if (!developer) return setStatus("Save your profile first. Pitches are posted under your profile.", true);

  const title = $<HTMLInputElement>("pitch-title").value.trim();
  const repo = $<HTMLInputElement>("pitch-repo").value.trim();
  const tags = $<HTMLInputElement>("pitch-tags").value.split(",").map(normalize).filter(Boolean);
  const file = $<HTMLInputElement>("pitch-video").files?.[0];

  if (!title) return setStatus("Give your project a name.", true);
  if (!safeUrl(repo)) return setStatus("Enter a repository link that starts with https://", true);
  if (file && !file.name.toLowerCase().endsWith(".mp4")) return setStatus("The server only accepts .mp4 videos.", true);
  if (file && file.size > MAX_VIDEO_BYTES) {
    return setStatus(`That video is ${(file.size / 1_048_576).toFixed(1)} MB. Choose one under 50 MB.`, true);
  }

  const submit = $<HTMLButtonElement>("pitch-submit");
  submit.disabled = true;
  try {
    let video_url: string | null = null;
    if (file) {
      setStatus("Uploading video…");
      const form = new FormData();
      form.append("file", file);
      video_url = (await api<{ video_url: string }>("/upload_video", { method: "POST", body: form })).video_url;
    }
    await api<Project>("/project", send("POST", {
      title, repo_url: repo, video_url, needs: { ...needsDraft }, tags, maintainer_id: developer.id,
    }));
    ($("composer") as HTMLFormElement).reset();
    Object.keys(needsDraft).forEach((k) => delete needsDraft[k]);
    renderDrafts();
    setStatus("Pitch posted.");
    await refresh();
  } catch (err) { fail(err); }
  finally { submit.disabled = false; }
}

// ---------- Wiring ----------
function fillLevels(id: string): void {
  $<HTMLSelectElement>(id).replaceChildren(...LEVELS.map((n) => el("option", { value: String(n), textContent: String(n) })));
}

function wireSkillAdder(inputId: string, levelId: string, buttonId: string, target: Skills): void {
  const input = $<HTMLInputElement>(inputId);
  const add = (): void => {
    const name = normalize(input.value);
    if (name) {
      target[name] = Number($<HTMLSelectElement>(levelId).value);
      input.value = "";
      renderDrafts();
    }
    input.focus();
  };
  $(buttonId).addEventListener("click", add);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); add(); } });
}

function wireInterestAdder(): void {
  const input = $<HTMLInputElement>("interest-input");
  const add = (): void => {
    const v = normalize(input.value);
    if (v) { interestsDraft.add(v); input.value = ""; renderDrafts(); }
    input.focus();
  };
  $("interest-add").addEventListener("click", add);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); add(); } });
}

async function init(): Promise<void> {
  fillLevels("skill-level");
  fillLevels("need-level");
  wireSkillAdder("skill-input", "skill-level", "skill-add", skillsDraft);
  wireSkillAdder("need-input", "need-level", "need-add", needsDraft);
  wireInterestAdder();
  $("profile-save").addEventListener("click", () => void saveProfile());
  $<HTMLFormElement>("composer").addEventListener("submit", (e) => void onPitch(e));
  renderDrafts();

  let savedId: string | null = null;
  storage(() => { savedId = localStorage.getItem(STORE_KEY); });
  if (savedId) {
    try { adoptDeveloper(await api<Developer>(`/developer/${savedId}`)); }
    catch { storage(() => localStorage.removeItem(STORE_KEY)); } // profile gone on server; start fresh
  }
  await refresh();
}

void init();
