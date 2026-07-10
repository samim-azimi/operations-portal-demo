import { Eye, EyeOff, MapPin, Pencil, Plus, Tag } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, ErrorBox, Loading } from "../components/UI";
import { useTranslation } from "../i18n";

export default function WorkspaceSettings() {
  const { t } = useTranslation();
  const [categories, setCategories] = useState(null);
  const [locations, setLocations] = useState(null);
  const [categoryName, setCategoryName] = useState("");
  const [locationName, setLocationName] = useState("");
  const [error, setError] = useState("");

  function load() {
    Promise.all([
      api("/categories"),
      api("/locations?include_inactive=true"),
    ])
      .then(([categoryData, locationData]) => {
        setCategories(categoryData);
        setLocations(locationData);
      })
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function addCategory(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/categories", {
        method: "POST",
        body: JSON.stringify({
          name: categoryName,
          description: `${categoryName} support requests`,
          is_active: true,
        }),
      });
      setCategoryName("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function addLocation(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/locations", {
        method: "POST",
        body: JSON.stringify({
          name: locationName,
          is_active: true,
          sort_order: locations?.length || 0,
        }),
      });
      setLocationName("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function update(type, item, changes = {}) {
    setError("");
    try {
      const payload = type === "categories"
        ? { name: item.name, description: item.description, is_active: item.is_active, ...changes }
        : { name: item.name, sort_order: item.sort_order, is_active: item.is_active, ...changes };
      await api(`/${type}/${item.id}`, { method: "PUT", body: JSON.stringify(payload) });
      load();
    } catch (err) { setError(err.message); }
  }

  function rename(type, item) {
    const name = window.prompt(`Rename ${item.name}:`, item.name);
    if (name?.trim() && name.trim() !== item.name) update(type, item, { name: name.trim() });
  }

  if (!categories || !locations) {
    return (
      <>
        <ErrorBox error={error} />
        <Loading />
      </>
    );
  }

  return (
    <div>
      <div className="pagehead">
        <div>
          <span className="eyebrow">{t("workspace")}</span>
          <h1>{t("settingsTitle")}</h1>
          <p>{t("settingsIntro")}</p>
        </div>
      </div>
      <ErrorBox error={error} />
      <div className="settings-grid">
        <section className="panel">
          <div className="panel-title">
            <div><span className="eyebrow">{t("routeRequest")}</span><h2>{t("ticketCategories")}</h2></div>
            <Tag />
          </div>
          <form className="inline-create" onSubmit={addCategory}>
            <input placeholder="Add a category" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} required />
            <button className="primary"><Plus /> {t("add")}</button>
          </form>
          <div className="settings-list">
            {categories.map((item) => (
              <article key={item.id}>
                <div><strong>{item.name}</strong><span>{item.description || "No description"}</span></div>
                <Badge type={item.is_active ? "resolved" : "closed"}>{item.is_active ? t("active") : t("hidden")}</Badge>
                <div className="row-actions"><button className="icon" title="Rename category" onClick={() => rename("categories", item)}><Pencil /></button>
                  <button className="icon" title={item.is_active ? "Hide category" : "Restore category"} onClick={() => update("categories", item, {is_active: !item.is_active})}>{item.is_active ? <EyeOff/> : <Eye/>}</button></div>
              </article>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">
            <div><span className="eyebrow">{t("location")}</span><h2>{t("supportLocations")}</h2></div>
            <MapPin />
          </div>
          <form className="inline-create" onSubmit={addLocation}>
            <input placeholder="Add a location" value={locationName} onChange={(event) => setLocationName(event.target.value)} required />
            <button className="primary"><Plus /> {t("add")}</button>
          </form>
          <div className="settings-list">
            {locations.map((item) => (
              <article key={item.id}>
                <div><strong>{item.name}</strong><span>Sort order {item.sort_order}</span></div>
                <Badge type={item.is_active ? "resolved" : "closed"}>{item.is_active ? t("active") : t("hidden")}</Badge>
                <div className="row-actions"><button className="icon" title="Rename location" onClick={() => rename("locations", item)}><Pencil /></button>
                  <button className="icon" title={item.is_active ? "Hide location" : "Restore location"} onClick={() => update("locations", item, {is_active: !item.is_active})}>{item.is_active ? <EyeOff/> : <Eye/>}</button></div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
