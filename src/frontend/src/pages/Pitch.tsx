import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, json, MAX_VIDEO_BYTES, safeUrl, type Project, type RepoInfo, type Skills } from "../api";
import { Notice, SkillEditor, TagEditor, msg } from "../components";

export default function Pitch() {
  const { id } = useParams();
  const editing = id !== undefined;
  const navigate = useNavigate();
  const [repo, setRepo] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [needs, setNeeds] = useState<Skills>({});
  const [tags, setTags] = useState<string[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    if (!editing) return;
    api<Project>(`/project/${id}`).then((p) => {
      setRepo(p.repo_url); setTitle(p.title); setDescription(p.description ?? "");
      setNeeds(p.needs); setTags(p.tags); setVideoUrl(p.video_url);
    }).catch((e) => setError(msg(e)));
  }, [editing, id]);

  async function fetchRepo() {
    if (!safeUrl(repo)) return setError("Enter a GitHub or GitLab repository link that starts with https://");
    setBusy(true); setError(""); setInfo("");
    try {
      const r = await api<RepoInfo>(`/repo/inspect?url=${encodeURIComponent(repo)}`);
      setRepo(r.repo_url);
      setTitle((t) => t || r.title);
      setDescription((d) => d || r.description || "");
      setNeeds((n) => ({ ...r.needs, ...n }));
      setTags((t) => [...new Set([...t, ...r.tags])]);
      setInfo(`Filled in from the repository (${r.stars} stars). Adjust anything that's off.`);
    } catch (e) { setError(msg(e)); } finally { setBusy(false); }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return setError("Give your project a name.");
    if (file && !file.name.toLowerCase().endsWith(".mp4")) return setError("Only .mp4 videos are accepted.");
    if (file && file.size > MAX_VIDEO_BYTES) return setError(`That video is ${(file.size / 1_048_576).toFixed(1)} MB. Choose one under 50 MB.`);
    setBusy(true); setError(""); setInfo("");
    try {
      let video = videoUrl;
      if (file) {
        setInfo("Uploading video…");
        const form = new FormData();
        form.append("file", file);
        video = (await api<{ video_url: string }>("/upload_video", { method: "POST", body: form })).video_url;
      }
      const body = { title: title.trim(), description: description.trim() || null, repo_url: repo.trim(), video_url: video, needs, tags };
      await api(editing ? `/project/${id}` : "/project", json(editing ? "PUT" : "POST", body));
      navigate("/projects");
    } catch (err) { setError(msg(err)); setInfo(""); } finally { setBusy(false); }
  }

  return (
    <form className="column form" onSubmit={submit}>
      <h2>{editing ? "Edit project" : "Pitch your project"}</h2>
      <Notice error={error} info={info} />
      <label htmlFor="repo">Repository link (GitHub or GitLab)</label>
      <div className="add-row">
        <input id="repo" type="text" inputMode="url" value={repo} placeholder="https://github.com/you/project" onChange={(e) => setRepo(e.target.value)} />
        <button type="button" className="secondary" disabled={busy} onClick={fetchRepo}>Fill from repo</button>
      </div>
      <label htmlFor="title">Project name</label>
      <input id="title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      <label htmlFor="desc">What does it do?</label>
      <textarea id="desc" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
      <SkillEditor label="Skills you need and the level" value={needs} onChange={setNeeds} placeholder="e.g. sql" />
      <TagEditor label="Tags" value={tags} onChange={setTags} placeholder="e.g. open source" />
      <label htmlFor="video">Pitch video (MP4, up to 50 MB)</label>
      <input id="video" type="file" accept="video/mp4,.mp4" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      {videoUrl && !file && <p className="note">Current video kept. <button type="button" className="link" onClick={() => setVideoUrl(null)}>Remove it</button></p>}
      <button type="submit" className="block" disabled={busy}>{editing ? "Save changes" : "Post pitch"}</button>
    </form>
  );
}
