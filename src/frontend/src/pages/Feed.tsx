import { useEffect, useState } from "react";
import { api, json, safeUrl, type FeedProject, type SwipeAction } from "../api";
import { useAuth } from "../auth";
import { Chip, Meter, Notice, msg } from "../components";

export function ProjectBody({ p }: { p: FeedProject | (Omit<FeedProject, "match_score" | "skill_fit" | "interest_fit"> & Partial<FeedProject>) }) {
  const { me } = useAuth();
  const mine = me?.skills ?? {};
  const interests = new Set(me?.interests ?? []);
  const repo = safeUrl(p.repo_url);
  const video = safeUrl(p.video_url);
  return (
    <>
      <div className="post-head">
        <strong>{p.title}</strong>
        {p.match_score !== undefined && <span className="score">{Math.round(p.match_score * 100)}% match</span>}
      </div>
      {p.description && <p className="desc">{p.description}</p>}
      {repo && <p><a href={repo} target="_blank" rel="noopener noreferrer">View repository</a></p>}
      {video && <video src={video} controls preload="metadata" />}
      <ul className="chips">
        {Object.entries(p.needs).map(([k, v]) => <Chip key={k} shared={(mine[k] ?? 0) >= v}>{`${k} ${v}`}</Chip>)}
        {p.tags.map((t) => <Chip key={t} shared={interests.has(t)}>{t}</Chip>)}
      </ul>
      {p.skill_fit !== undefined && p.interest_fit !== undefined && <Meter skill={p.skill_fit} interest={p.interest_fit} />}
    </>
  );
}

export default function Feed() {
  const [items, setItems] = useState<FeedProject[] | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => { api<FeedProject[]>("/feed").then(setItems).catch((e) => setError(msg(e))); }, []);

  async function swipe(p: FeedProject, action: SwipeAction) {
    try {
      await api("/swipe", json("POST", { project_id: p.id, action }));
      setItems((cur) => cur?.filter((x) => x.id !== p.id) ?? null);
      setError(""); setInfo(action === "APPLY" ? `Applied to ${p.title}.` : "");
    } catch (e) { setError(msg(e)); }
  }

  return (
    <section className="column">
      <h2>Projects for you</h2>
      <Notice error={error} info={info} />
      {items === null && !error && <p className="empty">Loading…</p>}
      {items?.length === 0 && <p className="empty">You've seen every project. Pitch your own, or check back soon.</p>}
      <ol className="posts">
        {items?.map((p) => (
          <li className="post" key={p.id}>
            <ProjectBody p={p} />
            <div className="actions">
              <button type="button" className="secondary" onClick={() => swipe(p, "SKIP")}>Skip</button>
              <button type="button" className="secondary" onClick={() => swipe(p, "LIKE")}>Like</button>
              <button type="button" onClick={() => swipe(p, "APPLY")}>Apply</button>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
