// ---------- Types ----------
interface Profile {
  skills: Set<string>;
  interests: Set<string>;
}

interface Project {
  id: string;
  name: string;
  summary: string;
  skills: string[];
  topics: string[];
}

interface Post {
  id: string;
  author: string;
  text: string;
  tags: string[];
  videoUrl?: string;
  createdAt: number;
}

interface Scored<T> {
  item: T;
  score: number; // 0 to 1
  sharedSkills: string[];
  sharedTopics: string[];
}

// ---------- Constants and sample data ----------
const MAX_VIDEO_BYTES = 50 * 1024 * 1024;
const DAY_MS = 86_400_000;

const projects: Project[] = [
  { id: "p1", name: "tidepool", summary: "A static site generator with a plugin system. Needs docs and a11y help.", skills: ["typescript", "docs", "accessibility"], topics: ["web", "accessibility"] },
  { id: "p2", name: "gridwatch", summary: "Open grid-load data tools for researchers and city planners.", skills: ["python", "data", "visualization"], topics: ["climate", "energy"] },
  { id: "p3", name: "lumen-cli", summary: "A fast command line image optimizer. Looking for Rust contributors.", skills: ["rust", "cli", "testing"], topics: ["performance", "tooling"] },
  { id: "p4", name: "openclinic", summary: "Scheduling software for small community clinics.", skills: ["typescript", "design", "postgres"], topics: ["health", "web"] },
];

const posts: Post[] = [
  { id: "s1", author: "Maya", text: "Tidepool's plugin API is stable now. We need people to write guides and test screen reader flows.", tags: ["docs", "accessibility", "typescript"], createdAt: Date.now() - 2 * 3_600_000 },
  { id: "s2", author: "Dev", text: "Looking for a second maintainer for lumen-cli. Rust experience helps, but good tests matter more.", tags: ["rust", "cli", "testing"], createdAt: Date.now() - 1 * DAY_MS },
  { id: "s3", author: "Ines", text: "Gridwatch now ingests hourly data from three regions. Help with charts would be great.", tags: ["python", "visualization", "climate"], createdAt: Date.now() - 4 * DAY_MS },
];

// ---------- State ----------
const profile: Profile = {
  skills: new Set(["typescript", "docs"]),
  interests: new Set(["accessibility"]),
};

// ---------- Matching algorithm ----------
const normalize = (s: string): string => s.trim().toLowerCase();

function overlap(a: Iterable<string>, b: Set<string>): string[] {
  return [...a].map(normalize).filter((x) => b.has(x));
}

/** Score = 60% skill fit + 40% interest fit, each as share of the item's needs covered. */
function scoreProject(p: Project): Scored<Project> {
  const sharedSkills = overlap(p.skills, profile.skills);
  const sharedTopics = overlap(p.topics, profile.interests);
  const skillFit = p.skills.length ? sharedSkills.length / p.skills.length : 0;
  const topicFit = p.topics.length ? sharedTopics.length / p.topics.length : 0;
  return { item: p, score: 0.6 * skillFit + 0.4 * topicFit, sharedSkills, sharedTopics };
}

/** Posts rank by tag overlap with the profile, with a gentle recency boost. */
function scorePost(p: Post): Scored<Post> {
  const all = new Set([...profile.skills, ...profile.interests]);
  const shared = overlap(p.tags, all);
  const tagFit = p.tags.length ? shared.length / p.tags.length : 0;
  const ageDays = (Date.now() - p.createdAt) / DAY_MS;
  const recency = 1 / (1 + ageDays);
  return { item: p, score: 0.75 * tagFit + 0.25 * recency, sharedSkills: shared, sharedTopics: [] };
}

// ---------- DOM helpers (textContent only, so user text is never parsed as HTML) ----------
function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<HTMLElementTagNameMap[K]> = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function $<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing element #${id}`);
  return node as T;
}

function timeAgo(ts: number): string {
  const mins = Math.round((Date.now() - ts) / 60_000);
  if (mins < 60) return `${Math.max(mins, 1)} min ago`;
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
  return `${Math.round(mins / 1440)} d ago`;
}

// ---------- Rendering ----------
function renderChipList(target: HTMLElement, values: Set<string>): void {
  target.replaceChildren(
    ...[...values].map((v) =>
      el("li", { className: "chip" }, v,
        el("button", {
          type: "button",
          ariaLabel: `Remove ${v}`,
          textContent: "×",
          onclick: () => { values.delete(v); renderAll(); },
        }))
    )
  );
}

function renderPost({ item: p, sharedSkills }: Scored<Post>): HTMLElement {
  const chips = el("ul", { className: "chips" },
    ...p.tags.map((t) => el("li", { className: sharedSkills.includes(normalize(t)) ? "chip shared" : "chip" }, t)));
  const card = el("li", { className: "post" },
    el("div", { className: "post-head" }, el("strong", {}, p.author), el("time", {}, timeAgo(p.createdAt))),
    el("p", {}, p.text));
  if (p.videoUrl) {
    card.append(el("video", { src: p.videoUrl, controls: true, preload: "metadata" }));
  }
  card.append(chips);
  return card;
}

function renderMatch({ item: p, score, sharedSkills, sharedTopics }: Scored<Project>): HTMLElement {
  const filled = Math.round(score * 5);
  const meter = el("div", { className: "meter", role: "img", ariaLabel: `Match ${filled} out of 5` },
    ...[0, 1, 2, 3, 4].map((i) => el("span", { className: i < filled ? "on" : "" })));
  const why = [...sharedSkills.map((s) => `skill: ${s}`), ...sharedTopics.map((t) => `interest: ${t}`)];
  return el("li", { className: "match" },
    el("h3", {}, p.name),
    el("p", {}, p.summary),
    meter,
    el("p", { className: "why" }, why.length ? `Matches your ${why.join(", ")}` : "No overlap with your profile yet"));
}

function renderAll(): void {
  renderChipList($("skill-list"), profile.skills);
  renderChipList($("interest-list"), profile.interests);

  const rankedPosts = posts.map(scorePost).sort((a, b) => b.score - a.score);
  $("feed-list").replaceChildren(...rankedPosts.map(renderPost));

  const rankedProjects = projects.map(scoreProject).sort((a, b) => b.score - a.score);
  $("match-list").replaceChildren(
    ...(rankedProjects.some((m) => m.score > 0)
      ? rankedProjects.map(renderMatch)
      : [el("li", { className: "empty" }, "Add skills or interests to see matches.")])
  );
}

// ---------- Events ----------
function wireAdder(inputId: string, buttonId: string, target: Set<string>): void {
  const input = $<HTMLInputElement>(inputId);
  const add = (): void => {
    const v = normalize(input.value);
    if (v) { target.add(v); input.value = ""; renderAll(); }
    input.focus();
  };
  $(buttonId).addEventListener("click", add);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); add(); } });
}

function showError(msg: string): void {
  const box = $("composer-error");
  box.textContent = msg;
  box.hidden = !msg;
}

function onSubmit(e: SubmitEvent): void {
  e.preventDefault();
  const text = $<HTMLTextAreaElement>("post-text").value.trim();
  const tags = $<HTMLInputElement>("post-tags").value.split(",").map(normalize).filter(Boolean);
  const file = $<HTMLInputElement>("post-video").files?.[0];

  if (!text && !file) return showError("Write something or attach a video before posting.");
  if (file && !file.type.startsWith("video/")) return showError("That file isn't a video. Choose an MP4, WebM or MOV.");
  if (file && file.size > MAX_VIDEO_BYTES) {
    return showError(`That video is ${(file.size / 1_048_576).toFixed(1)} MB. Choose one under 50 MB.`);
  }

  showError("");
  posts.unshift({
    id: crypto.randomUUID(),
    author: "You",
    text,
    tags,
    videoUrl: file ? URL.createObjectURL(file) : undefined, // TODO: upload to your backend instead
    createdAt: Date.now(),
  });
  (e.target as HTMLFormElement).reset();
  renderAll();
}

wireAdder("skill-input", "skill-add", profile.skills);
wireAdder("interest-input", "interest-add", profile.interests);
$<HTMLFormElement>("composer").addEventListener("submit", onSubmit);
renderAll();