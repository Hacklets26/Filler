import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Project } from "../api";
import { Notice, msg } from "../components";
import { ProjectBody } from "./Feed";

export default function MyProjects() {
  const [items, setItems] = useState<Project[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Project[]>("/me/projects").then(setItems).catch((e) => setError(msg(e))); }, []);

  async function remove(p: Project) {
    if (!window.confirm(`Delete "${p.title}"? Its video and all applications will be removed.`)) return;
    try { await api(`/project/${p.id}`, { method: "DELETE" }); setItems((c) => c?.filter((x) => x.id !== p.id) ?? null); }
    catch (e) { setError(msg(e)); }
  }

  return (
    <section className="column">
      <h2>My projects</h2>
      <Notice error={error} />
      {items?.length === 0 && <p className="empty">You haven't pitched anything yet. <Link to="/pitch">Pitch your first project.</Link></p>}
      <ol className="posts">
        {items?.map((p) => (
          <li className="post" key={p.id}>
            <ProjectBody p={p} />
            <div className="actions">
              <Link className="button secondary" to={`/projects/${p.id}/edit`}>Edit</Link>
              <button type="button" className="danger" onClick={() => remove(p)}>Delete</button>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
