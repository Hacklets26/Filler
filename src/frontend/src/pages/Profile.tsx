import { useState } from "react";
import { api, json, type Developer } from "../api";
import { useAuth } from "../auth";
import { Notice, SkillEditor, TagEditor, msg } from "../components";

export default function Profile() {
  const { me, setMe } = useAuth();
  const [name, setName] = useState(me?.name ?? "");
  const [skills, setSkills] = useState(me?.skills ?? {});
  const [interests, setInterests] = useState(me?.interests ?? []);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function save() {
    if (!name.trim()) return setError("Enter your name before saving.");
    try {
      setMe(await api<Developer>("/me", json("PUT", { name: name.trim(), skills, interests })));
      setError(""); setInfo("Profile saved.");
    } catch (e) { setError(msg(e)); setInfo(""); }
  }

  return (
    <section className="column form">
      <h2>Your profile</h2>
      <Notice error={error} info={info} />
      <label htmlFor="name">Name</label>
      <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
      <SkillEditor label="Skills and your level (1 to 5)" value={skills} onChange={setSkills} placeholder="e.g. python" />
      <TagEditor label="Interests" value={interests} onChange={setInterests} placeholder="e.g. data" />
      <button type="button" className="block" onClick={save}>Save profile</button>
    </section>
  );
}
