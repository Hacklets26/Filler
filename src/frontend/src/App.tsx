import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Feed from "./pages/Feed";
import Pitch from "./pages/Pitch";
import MyProjects from "./pages/MyProjects";
import Applications from "./pages/Applications";
import Profile from "./pages/Profile";
import { Login, AuthCallback } from "./pages/Login";
import { ThemeToggle } from "./theme";

function Shell() {
  const { me, ready, signOut } = useAuth();
  if (!ready) return <p className="empty page">Loading…</p>;
  if (!me) return <Navigate to="/login" replace />;
  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="brand">Patchwork</NavLink>
        <nav aria-label="Main">
          <NavLink to="/" end>Feed</NavLink>
          <NavLink to="/pitch">Pitch a project</NavLink>
          <NavLink to="/projects">My projects</NavLink>
          <NavLink to="/applications">Your interest</NavLink>
          <NavLink to="/profile">Profile</NavLink>
        </nav>
        <ThemeToggle />
        <div className="who">
          {me.avatar_url && <img src={me.avatar_url} alt="" width={28} height={28} />}
          <span>{me.login}</span>
          <button type="button" className="secondary" onClick={signOut}>Log out</button>
        </div>
      </header>
      <main className="page"><Outlet /></main>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth" element={<AuthCallback />} />
      <Route element={<Shell />}>
        <Route index element={<Feed />} />
        <Route path="pitch" element={<Pitch />} />
        <Route path="projects" element={<MyProjects />} />
        <Route path="projects/:id/edit" element={<Pitch />} />
        <Route path="applications" element={<Applications />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
