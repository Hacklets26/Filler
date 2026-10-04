"use strict";
// ---------- Config ----------
const API_BASE = "https://backend.ifamished.com";
const MAX_VIDEO_BYTES = 50 * 1024 * 1024;
const STORE_KEY = "patchwork.developerId";
const LEVELS = [1, 2, 3, 4, 5];
// ---------- API client ----------
class ApiError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}
async function api(path, init = {}) {
    let res;
    try {
        res = await fetch(API_BASE + path, init);
    }
    catch {
        throw new ApiError(0, "Can't reach the server. Check it is running, and that this page isn't on https while the API is on http.");
    }
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        }
        catch { /* keep statusText */ }
        throw new ApiError(res.status, detail);
    }
    return res.json();
}
const send = (method, body) => ({
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
});
// ---------- State ----------
let developer = null;
let feed = [];
let allProjects = [];
let applied = new Set();
const skillsDraft = {};
const interestsDraft = new Set();
const needsDraft = {};
// ---------- Helpers ----------
const normalize = (s) => s.trim().toLowerCase();
function $(id) {
    const node = document.getElementById(id);
    if (!node)
        throw new Error(`Missing element #${id}`);
    return node;
}
// textContent only, so user text is never parsed as HTML
function el(tag, props = {}, ...children) {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
}
/** Only allow http(s) links so a saved "javascript:" URL can't run. */
function safeUrl(raw) {
    if (!raw)
        return null;
    try {
        const u = new URL(raw);
        return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
    }
    catch {
        return null;
    }
}
function setStatus(msg, bad = false) {
    const box = $("status");
    box.textContent = msg;
    box.hidden = !msg;
    box.className = bad ? "status bad" : "status";
}
const fail = (e) => setStatus(e instanceof Error ? e.message : "Something went wrong.", true);
function storage(op) { try {
    op();
}
catch { /* storage may be blocked */ } }
const appliedKey = (id) => `patchwork.applied.${id}`;
// ---------- Rendering ----------
function renderChips(target, entries) {
    target.replaceChildren(...entries.map(({ label, onRemove }) => el("li", { className: "chip" }, label, el("button", { type: "button", ariaLabel: `Remove ${label}`, textContent: "×", onclick: onRemove }))));
}
function renderDrafts() {
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
function renderProject(p) {
    const mySkills = developer?.skills ?? {};
    const myInterests = new Set((developer?.interests ?? []).map(normalize));
    const head = el("div", { className: "post-head" }, el("strong", {}, p.title));
    if (p.match_score !== undefined) {
        head.append(el("span", { className: "score" }, `${Math.round(p.match_score * 100)}% match`));
    }
    const card = el("li", { className: "post" }, head);
    const repo = safeUrl(p.repo_url);
    if (repo)
        card.append(el("p", {}, el("a", { href: repo, target: "_blank", rel: "noopener noreferrer" }, "View repository")));
    const video = safeUrl(p.video_url);
    if (video)
        card.append(el("video", { src: video, controls: true, preload: "metadata" }));
    const needs = Object.entries(p.needs ?? {}).map(([skill, level]) => el("li", { className: (mySkills[skill] ?? 0) >= level ? "chip shared" : "chip" }, `${skill} ${level}`));
    const tags = (p.tags ?? []).map((t) => el("li", { className: myInterests.has(normalize(t)) ? "chip shared" : "chip" }, t));
    if (needs.length || tags.length)
        card.append(el("ul", { className: "chips" }, ...needs, ...tags));
    if (developer) {
        const act = (action, label, secondary) => el("button", { type: "button", textContent: label, className: secondary ? "secondary" : "", onclick: () => swipe(p, action) });
        card.append(el("div", { className: "actions" }, act("SKIP", "Skip", true), act("LIKE", "Like", true), act("APPLY", "Apply", false)));
    }
    return card;
}
function renderApplied() {
    const mine = allProjects.filter((p) => applied.has(p.id));
    $("match-list").replaceChildren(...(mine.length
        ? mine.map((p) => {
            const repo = safeUrl(p.repo_url);
            return el("li", { className: "match" }, el("h3", {}, p.title), repo ? el("p", {}, el("a", { href: repo, target: "_blank", rel: "noopener noreferrer" }, "Open repository")) : el("p", {}, "No repository link"));
        })
        : [el("li", { className: "empty" }, "Projects you apply to will show up here.")]));
}
function renderFeed() {
    const list = developer ? feed : allProjects;
    $("feed-list").replaceChildren(...(list.length
        ? list.map(renderProject)
        : [el("li", { className: "empty" }, developer ? "You've seen every project. Check back soon." : "No projects yet. Pitch the first one.")]));
    renderApplied();
}
// ---------- Data flow ----------
async function refresh() {
    try {
        const [projects, ranked] = await Promise.all([
            api("/projects"),
            developer ? api(`/feed/${developer.id}`) : Promise.resolve([]),
        ]);
        allProjects = projects;
        feed = ranked;
        renderFeed();
    }
    catch (e) {
        fail(e);
    }
}
function adoptDeveloper(d) {
    developer = d;
    $("dev-name").value = d.name;
    Object.keys(skillsDraft).forEach((k) => delete skillsDraft[k]);
    Object.assign(skillsDraft, d.skills);
    interestsDraft.clear();
    d.interests.forEach((i) => interestsDraft.add(i));
    storage(() => localStorage.setItem(STORE_KEY, String(d.id)));
    storage(() => {
        const saved = localStorage.getItem(appliedKey(d.id));
        applied = new Set(saved ? JSON.parse(saved) : []);
    });
    renderDrafts();
}
async function saveProfile() {
    const name = $("dev-name").value.trim();
    if (!name)
        return setStatus("Enter your name before saving.", true);
    const body = { name, skills: { ...skillsDraft }, interests: [...interestsDraft] };
    try {
        const d = developer
            ? await api(`/developer/${developer.id}`, send("PUT", body))
            : await api("/developer", send("POST", body));
        adoptDeveloper(d);
        setStatus("Profile saved.");
        await refresh();
    }
    catch (e) {
        fail(e);
    }
}
async function swipe(p, action) {
    if (!developer)
        return;
    try {
        await api("/swipe", send("POST", { developer_id: developer.id, project_id: p.id, action }));
        if (action === "APPLY") {
            applied.add(p.id);
            const id = developer.id;
            storage(() => localStorage.setItem(appliedKey(id), JSON.stringify([...applied])));
            setStatus(`Applied to ${p.title}.`);
        }
        else {
            setStatus("");
        }
        developer.swipe_history.push(p.id);
        await refresh();
    }
    catch (e) {
        fail(e instanceof ApiError && e.status === 409 ? new Error("You already responded to this project.") : e);
    }
}
async function onPitch(e) {
    e.preventDefault();
    if (!developer)
        return setStatus("Save your profile first. Pitches are posted under your profile.", true);
    const title = $("pitch-title").value.trim();
    const repo = $("pitch-repo").value.trim();
    const tags = $("pitch-tags").value.split(",").map(normalize).filter(Boolean);
    const file = $("pitch-video").files?.[0];
    if (!title)
        return setStatus("Give your project a name.", true);
    if (!safeUrl(repo))
        return setStatus("Enter a repository link that starts with https://", true);
    if (file && !file.name.toLowerCase().endsWith(".mp4"))
        return setStatus("The server only accepts .mp4 videos.", true);
    if (file && file.size > MAX_VIDEO_BYTES) {
        return setStatus(`That video is ${(file.size / 1048576).toFixed(1)} MB. Choose one under 50 MB.`, true);
    }
    const submit = $("pitch-submit");
    submit.disabled = true;
    try {
        let video_url = null;
        if (file) {
            setStatus("Uploading video…");
            const form = new FormData();
            form.append("file", file);
            video_url = (await api("/upload_video", { method: "POST", body: form })).video_url;
        }
        await api("/project", send("POST", {
            title, repo_url: repo, video_url, needs: { ...needsDraft }, tags, maintainer_id: developer.id,
        }));
        $("composer").reset();
        Object.keys(needsDraft).forEach((k) => delete needsDraft[k]);
        renderDrafts();
        setStatus("Pitch posted.");
        await refresh();
    }
    catch (err) {
        fail(err);
    }
    finally {
        submit.disabled = false;
    }
}
// ---------- Wiring ----------
function fillLevels(id) {
    $(id).replaceChildren(...LEVELS.map((n) => el("option", { value: String(n), textContent: String(n) })));
}
function wireSkillAdder(inputId, levelId, buttonId, target) {
    const input = $(inputId);
    const add = () => {
        const name = normalize(input.value);
        if (name) {
            target[name] = Number($(levelId).value);
            input.value = "";
            renderDrafts();
        }
        input.focus();
    };
    $(buttonId).addEventListener("click", add);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") {
        e.preventDefault();
        add();
    } });
}
function wireInterestAdder() {
    const input = $("interest-input");
    const add = () => {
        const v = normalize(input.value);
        if (v) {
            interestsDraft.add(v);
            input.value = "";
            renderDrafts();
        }
        input.focus();
    };
    $("interest-add").addEventListener("click", add);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") {
        e.preventDefault();
        add();
    } });
}
async function init() {
    fillLevels("skill-level");
    fillLevels("need-level");
    wireSkillAdder("skill-input", "skill-level", "skill-add", skillsDraft);
    wireSkillAdder("need-input", "need-level", "need-add", needsDraft);
    wireInterestAdder();
    $("profile-save").addEventListener("click", () => void saveProfile());
    $("composer").addEventListener("submit", (e) => void onPitch(e));
    renderDrafts();
    let savedId = null;
    storage(() => { savedId = localStorage.getItem(STORE_KEY); });
    if (savedId) {
        try {
            adoptDeveloper(await api(`/developer/${savedId}`));
        }
        catch {
            storage(() => localStorage.removeItem(STORE_KEY));
        } // profile gone on server; start fresh
    }
    await refresh();
}
void init();
