import { ProjectsPanel } from "../components/ProjectsPanel";
import { NewEntryForm } from "../components/NewEntryForm";

async function fetchStatus() {
  const res = await fetch("/api/memory/status", { cache: "no-store" });
  if (!res.ok) {
    return { ok: false, detail: await res.text() };
  }
  return res.json();
}

export default async function DashboardPage() {
  const status = await fetchStatus();

  return (
    <div className="space-y-6">
      <section className="card">
        <h2 className="text-xl font-semibold">Stack Health</h2>
        <div className="grid md:grid-cols-3 gap-4 mt-3 text-sm">
          {status.services?.map((svc: any) => (
            <div
              key={svc.name}
              className={`rounded border px-3 py-2 ${
                svc.healthy
                  ? "border-emerald-500 text-emerald-300"
                  : "border-rose-600 text-rose-300"
              }`}
            >
              <div className="font-semibold">{svc.name}</div>
              <div>{svc.detail}</div>
            </div>
          ))}
        </div>
      </section>
      <ProjectsPanel />
      <NewEntryForm />
    </div>
  );
}
