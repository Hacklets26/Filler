import { useCallback, useEffect, useState } from "react";
import { api, safeUrl, type Application, type ApplicationStatus } from "../api";
import { Notice, msg } from "../components";

function Status({ status }: { status: ApplicationStatus }) {
  return <span className={`application-status ${status}`}>{status}</span>;
}

export default function Applications() {
  const [sent, setSent] = useState<Application[] | null>(null);
  const [received, setReceived] = useState<Application[] | null>(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [applications, incoming] = await Promise.all([
        api<Application[]>("/me/applications"),
        api<Application[]>("/me/incoming-applications"),
      ]);
      setSent(applications);
      setReceived(incoming);
      setError("");
    } catch (e) {
      setError(msg(e));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function review(application: Application, status: "accepted" | "declined") {
    setBusyId(application.application_id); setError(""); setInfo("");
    try {
      const updated = await api<Application>(
        `/applications/${application.application_id}`,
        { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) },
      );
      setReceived((current) => current?.map((item) =>
        item.application_id === updated.application_id ? updated : item,
      ) ?? null);
      setInfo(`${updated.developer.login}'s application was ${status}.`);
    } catch (e) {
      setError(msg(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="column applications-page">
      <div className="section-heading">
        <div><p className="eyebrow">Keep the conversation moving</p><h1>Applications</h1></div>
      </div>
      <Notice error={error} info={info} />

      <section className="application-section">
        <div className="subheading"><h2>Applications to join you</h2><span>{received?.length ?? "—"}</span></div>
        {received?.length === 0 && <p className="empty">Applications to your project pitches will appear here.</p>}
        <ol className="application-list">
          {received?.map((application) => (
            <li className="application-card" key={application.application_id}>
              <div className="application-card-heading">
                <div>
                  <p className="eyebrow">{application.project.title}</p>
                  <h3>{application.developer.name}</h3>
                  <a href={safeUrl(`https://github.com/${application.developer.login}`) ?? "#"}
                    target="_blank" rel="noopener noreferrer">@{application.developer.login} on GitHub ↗</a>
                </div>
                <Status status={application.status} />
              </div>
              {application.status === "pending" && (
                <div className="actions">
                  <button type="button" disabled={busyId !== null}
                    onClick={() => review(application, "accepted")}>
                    {busyId === application.application_id ? "Saving…" : "Accept"}
                  </button>
                  <button type="button" className="secondary" disabled={busyId !== null}
                    onClick={() => review(application, "declined")}>Decline</button>
                </div>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="application-section">
        <div className="subheading"><h2>Sent by you</h2><span>{sent?.length ?? "—"}</span></div>
        {sent?.length === 0 && <p className="empty">When you apply to a project, you can follow its status here.</p>}
        <ol className="application-list">
          {sent?.map((application) => (
            <li className="application-card" key={application.application_id}>
              <div className="application-card-heading">
                <div>
                  <p className="eyebrow">Application to</p>
                  <h3>{application.project.title}</h3>
                  <a href={safeUrl(application.project.repo_url) ?? "#"} target="_blank" rel="noopener noreferrer">Explore project ↗</a>
                </div>
                <Status status={application.status} />
              </div>
            </li>
          ))}
        </ol>
      </section>
    </section>
  );
}
