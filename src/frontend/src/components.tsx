import { useState, type ReactNode } from "react";
import type { Skills } from "./api";

const LEVELS = [1, 2, 3, 4, 5];
const norm = (s: string) => s.trim().toLowerCase();

export function Chip({ children, shared, onRemove }: { children: ReactNode; shared?: boolean; onRemove?: () => void }) {
  return (
    <li className={shared ? "chip shared" : "chip"}>
      {children}
      {onRemove && <button type="button" aria-label={`Remove ${String(children)}`} onClick={onRemove}>×</button>}
    </li>
  );
}

export function SkillEditor({ label, value, onChange, placeholder }: {
  label: string; value: Skills; onChange: (s: Skills) => void; placeholder: string;
}) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState(3);
  const add = () => { const n = norm(name); if (n) { onChange({ ...value, [n]: level }); setName(""); } };
  return (
    <div>
      <label>{label}</label>
      <div className="add-row">
        <input type="text" value={name} placeholder={placeholder} onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        <select aria-label="Level" value={level} onChange={(e) => setLevel(Number(e.target.value))}>
          {LEVELS.map((n) => <option key={n}>{n}</option>)}
        </select>
        <button type="button" onClick={add}>Add</button>
      </div>
      <ul className="chips">
        {Object.entries(value).map(([k, v]) => (
          <Chip key={k} onRemove={() => { const { [k]: _, ...rest } = value; onChange(rest); }}>{`${k} ${v}`}</Chip>
        ))}
      </ul>
    </div>
  );
}

export function TagEditor({ label, value, onChange, placeholder }: {
  label: string; value: string[]; onChange: (t: string[]) => void; placeholder: string;
}) {
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

/** Bars make the available ranking signals transparent. */
export function Meter({ skill, interest, text }: {
  skill: number | null; interest: number | null; text: number | null;
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
      {interest !== null && row("Interest fit", interest)}
      {text !== null && row("Project relevance", text)}
    </div>
  );
}

export const Notice = ({ error, info }: { error?: string; info?: string }) =>
  error ? <p className="status bad" role="alert">{error}</p> : info ? <p className="status" role="status">{info}</p> : null;

export const msg = (e: unknown): string => (e instanceof Error ? e.message : "Something went wrong.");
