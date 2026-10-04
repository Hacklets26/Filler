import { useCallback, useEffect, useMemo, useState } from "react";
import { api, json, safeUrl, type FeedProject, type Project, type SwipeAction } from "../api";
import { useAuth } from "../auth";
import { Chip, Meter, Notice, msg } from "../components";

type ProjectBodyData = FeedProject | (Project & Partial<Pick<
  FeedProject, "match_score" | "skill_fit" | "interest_fit" | "text_fit"
>>);

export function ProjectBody({ p }: { p: ProjectBodyData }) {
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
      {p.match_score !== undefined && (
        <Meter skill={p.skill_fit ?? null} interest={p.interest_fit ?? null} text={p.text_fit ?? null} />
      )}
    </>
  );
}

export default function Feed() {
  const [items, setItems] = useState<FeedProject[] | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [search, setSearch] = useState("");
  const [minimumMatch, setMinimumMatch] = useState(0);
  const [sortBy, setSortBy] = useState<"match" | "title">("match");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadFeed = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      setItems(await api<FeedProject[]>("/feed"));
    } catch (e) {
      setError(msg(e));
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void loadFeed(); }, [loadFeed]);

  const visibleItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return [...(items ?? [])]
      .filter((project) => project.match_score >= minimumMatch)
      .filter((project) => !query || [
        project.title, project.description ?? "", project.repo_url,
        ...project.tags, ...Object.keys(project.needs),
      ].some((value) => value.toLocaleLowerCase().includes(query)))
      .sort((a, b) => sortBy === "match"
        ? b.match_score - a.match_score || a.id - b.id
        : a.title.localeCompare(b.title));
  }, [items, minimumMatch, search, sortBy]);

  async function swipe(p: FeedProject, action: SwipeAction) {
    setBusyId(p.id); setError("");
    try {
      await api("/swipe", json("POST", { project_id: p.id, action }));
      setItems((cur) => cur?.filter((x) => x.id !== p.id) ?? null);
      setInfo(action === "APPLY" ? `You showed interest in ${p.title}. Track it in Your interest.` : "");
    } catch (e) { setError(msg(e)); setInfo(""); }
    finally { setBusyId(null); }
  }

  return (
    <section className="column">
      <div className="section-heading">
        <div><p className="eyebrow">A good place to start</p><h1>Find your next project</h1></div>
        <div className="feed-heading-actions">
          <span className="result-count">{visibleItems.length} matches</span>
          <button type="button" className="secondary refresh-button" onClick={() => void loadFeed()}
            disabled={refreshing} aria-label="Refresh project recommendations">
            <span aria-hidden="true" className={refreshing ? "refresh-icon spinning" : "refresh-icon"}>↻</span>
            {refreshing ? "Refreshing" : "Refresh"}
          </button>
        </div>
      </div>
      <Notice error={error} info={info} />
      <div className="feed-tools" aria-label="Filter projects">
        <label className="search-field">
          <span>Search</span>
          <input type="search" value={search} placeholder="Try Python, data, or a project name"
            onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label>
          <span>Minimum match</span>
          <select value={minimumMatch} onChange={(event) => setMinimumMatch(Number(event.target.value))}>
            <option value={0}>Any fit</option>
            <option value={0.5}>50% and up</option>
            <option value={0.7}>70% and up</option>
            <option value={0.85}>85% and up</option>
          </select>
        </label>
        <label>
          <span>Sort by</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as "match" | "title")}>
            <option value="match">Best match</option>
            <option value="title">Project name</option>
          </select>
        </label>
      </div>
      {items === null && !error && <p className="empty">Loading…</p>}
      {items === null && error && <div className="empty-card"><h2>Recommendations could not load</h2><p>Check your connection and try again.</p><button type="button" onClick={() => void loadFeed()}>Try again</button></div>}
      {items?.length === 0 && <div className="empty-card"><h2>Room to make a difference</h2><p>There are no new projects right now. Pitch a project of your own, or come back soon.</p></div>}
      {items && items.length > 0 && visibleItems.length === 0 && <p className="empty">No projects match those filters. Try a broader search.</p>}
      <ol className="posts">
        {visibleItems.map((p) => (
          <li className="post" key={p.id}>
            <ProjectBody p={p} />
            <div className="actions">
              <button type="button" className="secondary" disabled={busyId !== null} onClick={() => swipe(p, "SKIP")}>Pass</button>
              <button type="button" disabled={busyId !== null} onClick={() => swipe(p, "APPLY")}>
                {busyId === p.id ? "Sending…" : "Show interest"}
              </button>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
