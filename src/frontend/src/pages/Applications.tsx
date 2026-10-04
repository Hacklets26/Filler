import { useEffect, useState } from "react";
import { api, safeUrl, type Project } from "../api";
import { Notice, msg } from "../components";

export default function Applications() {
  const [items, setItems] = useState<Project[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Project[]>("/me/applications").then(setItems).catch((e) => setError(msg(e))); }, []);
  return (
    <section className="column">
      <h2>Projects you applied to</h2>
      <Notice error={error} />
      {items?.length === 0 && <p className="empty">Projects you apply to will show up here.</p>}
      <ol className="posts">
        {items?.map((p) => {
          const repo = safeUrl(p.repo_url);
          return (
            <li className="post" key={p.id}>
              <strong>{p.title}</strong>
              {repo ? <p><a href={repo} target="_blank" rel="noopener noreferrer">Open repository</a></p> : <p>No repository link</p>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
