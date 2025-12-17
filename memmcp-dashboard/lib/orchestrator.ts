const ORCHESTRATOR_URL =
  process.env.MEMMCP_ORCHESTRATOR_URL ?? "http://127.0.0.1:8075";

export async function callOrchestrator(
  path: string,
  init?: RequestInit,
): Promise<any> {
  const target = `${ORCHESTRATOR_URL}${path}`;
  const res = await fetch(target, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Orchestrator ${path} failed: ${res.status} ${detail}`);
  }
  return res.json();
}
