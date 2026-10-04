import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { Notice, msg } from "../components";

export function Login() {
  const { me, ready, loginUrl } = useAuth();
  if (ready && me) return <Navigate to="/" replace />;
  return (
    <main className="login">
      <h1>FILLER</h1>
      <p>Open source projects, matched to what you can do and what you care about.</p>
      <a className="button" href={loginUrl}>Continue with GitHub</a>
      <p className="note">We read your public profile to suggest skills from the languages in your repositories. You can edit them afterwards.</p>
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

  return <main className="login"><Notice error={error} info={error ? "" : "Signing you in…"} />{error && <a href="#/login">Back to login</a>}</main>;
}
