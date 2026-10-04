import { useState, type ReactNode } from "react";
import type { Skills } from "./api";

const SKILL_GROUPS = [
  { label: "Languages", skills: ["Bash", "C", "C++", "C#", "CSS", "Dart", "Elixir", "Go", "HTML", "Haskell", "Java", "JavaScript", "Kotlin", "Lua", "Makefile", "Objective-C", "Perl", "PHP", "Python", "R", "Ruby", "Rust", "Scala", "Shell", "SQL", "Swift", "TypeScript"] },
  { label: "Frontend", skills: ["Accessibility", "Angular", "React", "Svelte", "UI/UX", "Vue"] },
  { label: "Backend & data", skills: ["Django", "FastAPI", "GraphQL", "Machine Learning", "MongoDB", "Node.js", "PostgreSQL", "REST APIs", "SQLite"] },
  { label: "Tools", skills: ["AWS", "Docker", "Git", "Linux"] },
] as const;
const LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"] as const;
const norm = (s: string) => s.trim().toLowerCase();
const SKILL_LABELS = new Map(SKILL_GROUPS.flatMap((group) => group.skills.map((skill) => [norm(skill), skill] as const)));

export function getSkillLabel(name: string): string | undefined {
  return SKILL_LABELS.get(norm(name));
}

export function getSkillLevelLabel(value: number): (typeof LEVELS)[number] | null {
  if (value < 1) return null;
  if (value < 2) return LEVELS[0];
  if (value < 3) return LEVELS[1];
  if (value < 4) return LEVELS[2];
  return LEVELS[3];
}

export function Chip({ children, shared, skillLevel, onRemove }: {
  children: ReactNode; shared?: boolean; skillLevel?: number; onRemove?: () => void;
}) {
  const level = skillLevel === undefined ? null : getSkillLevelLabel(skillLevel);
  return (
    <li
      className={`chip${shared ? " shared" : ""}${skillLevel === undefined ? "" : " skill-chip"}`}
      data-level={level?.toLowerCase()}
      aria-label={level ? `${String(children)}: ${level}` : undefined}
    >
      {children}
      {onRemove && <button type="button" aria-label={`Remove ${String(children)}`} onClick={onRemove}>×</button>}
    </li>
  );
}

export function SkillEditor({ label, value, onChange }: {
  label: string; value: Skills; onChange: (s: Skills) => void;
}) {
  const cycle = (skill: string) => {
    const key = norm(skill);
    const existingKey = Object.keys(value).find((name) => norm(name) === key);
    const current = existingKey ? value[existingKey] ?? 0 : 0;
    const next = Object.fromEntries(
      Object.entries(value).filter(([name]) => norm(name) !== key),
    );
    if (current < 1) next[key] = 1;
    else if (current < LEVELS.length) next[key] = Math.floor(current) + 1;
    onChange(next);
  };

  return (
    <div role="group" aria-label={label}>
      <p className="skill-editor-label">{label}</p>
      <div className="skill-groups">
        {SKILL_GROUPS.map((group) => (
          <fieldset className="skill-group" key={group.label}>
            <legend>{group.label}</legend>
            <div className="skill-options">
              {group.skills.map((skill) => {
                const current = value[norm(skill)] ?? 0;
                const level = getSkillLevelLabel(current);
                return (
                  <button
                    className={`skill-option${level ? " selected" : ""}`}
                    data-level={level?.toLowerCase()}
                    type="button"
                    key={skill}
                    aria-label={`${skill}: ${level ?? "not selected"}. Click to change proficiency.`}
                    aria-pressed={level !== null}
                    onClick={() => cycle(skill)}
                  >
                    <span>{skill}</span>
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </div>
  );
}

export function TagEditor({ label, value, onChange, placeholder }: {
  label: string; value: string[]; onChange: (t: string[]) => void; placeholder: string;
}) {
  // Tags are kept as a normalized list so we avoid duplicates and inconsistent casing in saved profiles.
  const [text, setText] = useState("");
  const add = () => { const n = norm(text); if (n && !value.includes(n)) onChange([...value, n]); setText(""); };
  return (
    <div>
      <label>{label}</label>
      <div className="add-row">
        <input type="text" value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        <button type="button" onClick={add}>Add</button>
      </div>
      <ul className="chips">{value.map((t) => <Chip key={t} onRemove={() => onChange(value.filter((x) => x !== t))}>{t}</Chip>)}</ul>
    </div>
  );
}

/** The meter makes each ranking signal easy to scan in a single glance. */
export function Meter({ skill, interestRelevance }: {
  skill: number | null; interestRelevance: number | null;
}) {
  const row = (name: string, v: number) => (
    <div className="meter-row">
      <span>{name}</span>
      <div className="bar" role="meter" aria-label={name} aria-valuenow={Math.round(v * 100)} aria-valuemin={0} aria-valuemax={100}>
        <i style={{ width: `${Math.round(v * 100)}%` }} />
      </div>
      <b>{Math.round(v * 100)}%</b>
    </div>
  );
  return (
    <div className="meter">
      {skill !== null && row("Skill fit", skill)}
      {interestRelevance !== null && row("Interest & relevance", interestRelevance)}
    </div>
  );
}

export const Notice = ({ error, info }: { error?: string; info?: string }) =>
  error ? <p className="status bad" role="alert">{error}</p> : info ? <p className="status" role="status">{info}</p> : null;

export const msg = (e: unknown): string => (e instanceof Error ? e.message : "Something went wrong.");
