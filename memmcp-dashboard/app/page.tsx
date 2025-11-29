import { ProjectsPanel } from "../components/ProjectsPanel";
import { NewEntryForm } from "../components/NewEntryForm";
import { TelemetryPanel } from "../components/TelemetryPanel";
import { CompoundingPanel } from "../components/CompoundingPanel";

async function fetchStatus() {
  const res = await fetch("/api/memory/status", { cache: "no-store" });
  if (!res.ok) {
    return { ok: false, detail: await res.text() };
  }
  return res.json();
}

async function fetchTelemetryMetrics() {
  try {
    const res = await fetch("/api/telemetry/metrics", { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    return res.json();
  } catch (err) {
    console.warn("Telemetry metrics fetch failed", err);
    return null;
  }
}

async function fetchTradingMetrics() {
  try {
    const res = await fetch("/api/telemetry/trading", { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    return res.json();
  } catch (err) {
    console.warn("Trading metrics fetch failed", err);
    return null;
  }
}

export default async function DashboardPage() {
  const [status, telemetry, trading] = await Promise.all([
    fetchStatus(),
    fetchTelemetryMetrics(),
    fetchTradingMetrics(),
  ]);

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
      <CompoundingPanel trading={trading} />
      <TelemetryPanel queueMetrics={telemetry} tradingMetrics={trading} />
      <ProjectsPanel />
      <NewEntryForm />
    </div>
  );
}
