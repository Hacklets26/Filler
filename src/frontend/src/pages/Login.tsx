import { useEffect, useState } from "react";
import { Navigate, NavLink, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { Notice, msg } from "../components";

export function Login() {
  const { me, ready, loginUrl } = useAuth();
  if (ready && me) return <Navigate to="/" replace />;
  return (
    <main className="login-layout">
      <section className="login-copy">
        <NavLink to="/login" className="brand login-brand">Patchwork</NavLink>
        <p className="eyebrow">Good work grows together</p>
        <h1>Your next open-source chapter starts here.</h1>
        <p>Meet projects that need your skills, and maintainers who are glad you showed up.</p>
        <div className="login-art" aria-hidden="true">
          <span className="orbit-dot one" /><span className="orbit-dot two" /><span className="orbit-dot three" />
        </div>
      </section>
      <section className="login-card">
        <p className="eyebrow">For makers and maintainers</p>
        <h2>Find your people.</h2>
        <p>Sign in with GitHub to build your profile and find a project worth your time.</p>
        <a className="button" href={loginUrl}>Continue with GitHub <span aria-hidden="true">&nbsp;↗</span></a>
        <p className="note">We use your public GitHub profile to get you started. You control the skills and interests on your profile.</p>
      </section>
    </main>
  );
}

export function AuthCallback() {
  const [params] = useSearchParams();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setError("Login did not complete. Try again."); return; }
    signIn(token).then(() => navigate("/profile", { replace: true })).catch((e) => setError(msg(e)));
  }, [params, signIn, navigate]);

  return (
    <main className="callback-page">
      <section className="login-card">
        <NavLink to="/login" className="brand login-brand">Patchwork</NavLink>
        <h2>{error ? "We couldn't finish signing you in." : "Welcome to Patchwork"}</h2>
        <Notice error={error} info={error ? "" : "Checking your GitHub account…"} />
        {error && <NavLink className="button" to="/login">Back to sign in</NavLink>}
      </section>
    </main>
  );
}
