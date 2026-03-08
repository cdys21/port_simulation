import { RunRecord, ScenarioConfig, ScenarioRecord } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(payload.detail || "Request failed");
  }
  return response.json() as Promise<T>;
}

export async function fetchScenarios(): Promise<ScenarioRecord[]> {
  return handle<ScenarioRecord[]>(await fetch(`${API_BASE}/scenarios`));
}

export async function fetchRuns(): Promise<RunRecord[]> {
  return handle<RunRecord[]>(await fetch(`${API_BASE}/runs`));
}

export async function saveScenario(id: string, config: ScenarioConfig): Promise<ScenarioRecord> {
  return handle<ScenarioRecord>(
    await fetch(`${API_BASE}/scenarios/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }),
  );
}

export async function createScenario(config: ScenarioConfig): Promise<ScenarioRecord> {
  return handle<ScenarioRecord>(
    await fetch(`${API_BASE}/scenarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }),
  );
}

export async function createRun(scenarioId: string): Promise<RunRecord> {
  return handle<RunRecord>(
    await fetch(`${API_BASE}/scenarios/${scenarioId}/runs`, {
      method: "POST",
    }),
  );
}

export async function fetchRun(runId: string): Promise<RunRecord> {
  return handle<RunRecord>(await fetch(`${API_BASE}/runs/${runId}`));
}
