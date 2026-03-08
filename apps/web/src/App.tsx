import { useEffect, useMemo, useState } from "react";

import {
  createRun,
  createScenario,
  fetchRun,
  fetchRuns,
  fetchScenarios,
  saveScenario,
} from "./api";
import { RunRecord, ScenarioConfig, ScenarioRecord } from "./types";

type TabKey = "overview" | "yard" | "vessels" | "containers";

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function numberInput(
  value: number,
  onChange: (value: number) => void,
  step = 1,
  min?: number,
  max?: number,
) {
  return (
    <input
      className="field"
      type="number"
      value={Number.isFinite(value) ? value : 0}
      step={step}
      min={min}
      max={max}
      onChange={(event) => onChange(Number(event.target.value))}
    />
  );
}

function polylinePoints(values: number[], width: number, height: number): string {
  if (!values.length) {
    return "";
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

function metric(summary: Record<string, number>, key: string): number {
  return summary[key] ?? 0;
}

function formatDelta(value: number, digits = 1): string {
  const rounded = Number(value.toFixed(digits));
  if (rounded === 0) {
    return "0";
  }
  return `${rounded > 0 ? "+" : ""}${rounded}`;
}

function LineCard({
  title,
  data,
  keys,
}: {
  title: string;
  data: Array<Record<string, number>>;
  keys: Array<{ key: string; color: string; label: string }>;
}) {
  const width = 420;
  const height = 140;
  return (
    <div className="panel chart-card">
      <div className="panel-header">
        <h3>{title}</h3>
        <div className="legend">
          {keys.map((entry) => (
            <span key={entry.key}>
              <i style={{ backgroundColor: entry.color }} />
              {entry.label}
            </span>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
        <rect x="0" y="0" width={width} height={height} rx="12" className="chart-bg" />
        {keys.map((entry) => (
          <polyline
            key={entry.key}
            fill="none"
            stroke={entry.color}
            strokeWidth="3"
            points={polylinePoints(data.map((point) => point[entry.key] ?? 0), width, height)}
          />
        ))}
      </svg>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
  delta,
}: {
  label: string;
  value: string;
  accent?: string;
  delta?: string | null;
}) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong style={accent ? { color: accent } : undefined}>{value}</strong>
      {delta ? <small>{delta}</small> : <small>&nbsp;</small>}
    </div>
  );
}

export default function App() {
  const [scenarios, setScenarios] = useState<ScenarioRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [config, setConfig] = useState<ScenarioConfig | null>(null);
  const [activeRun, setActiveRun] = useState<RunRecord | null>(null);
  const [compareRunId, setCompareRunId] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Loading workspace...");

  useEffect(() => {
    void loadInitial();
  }, []);

  useEffect(() => {
    if (!activeRun || !["queued", "running"].includes(activeRun.status)) {
      return;
    }
    const handle = window.setInterval(async () => {
      const next = await fetchRun(activeRun.id);
      setActiveRun(next);
      setRuns((current) => {
        const remaining = current.filter((run) => run.id !== next.id);
        return [next, ...remaining];
      });
      if (next.status === "completed") {
        setMessage("Run completed.");
      }
      if (next.status === "failed") {
        setMessage(next.error || "Run failed.");
      }
    }, 1500);
    return () => window.clearInterval(handle);
  }, [activeRun]);

  async function loadInitial() {
    try {
      const [nextScenarios, nextRuns] = await Promise.all([fetchScenarios(), fetchRuns()]);
      setScenarios(nextScenarios);
      setRuns(nextRuns);
      if (nextScenarios.length) {
        const initialScenario = nextScenarios[0];
        setSelectedId(initialScenario.id);
        setConfig(clone(initialScenario.config));
      }
      if (nextRuns.length) {
        setActiveRun(nextRuns[0]);
      }
      setMessage("Workspace ready.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  }

  async function refreshScenarios() {
    try {
      const next = await fetchScenarios();
      setScenarios(next);
      if (!next.length) {
        return;
      }
      const keepId = next.some((scenario) => scenario.id === selectedId) ? selectedId : next[0].id;
      const nextSelected = next.find((scenario) => scenario.id === keepId) ?? next[0];
      setSelectedId(nextSelected.id);
      setConfig(clone(nextSelected.config));
      setMessage("Scenario library refreshed.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  }

  async function refreshRuns() {
    try {
      const next = await fetchRuns();
      setRuns(next);
      if (activeRun) {
        const refreshed = next.find((run) => run.id === activeRun.id);
        if (refreshed) {
          setActiveRun(refreshed);
        }
      }
    } catch (error) {
      setMessage((error as Error).message);
    }
  }

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.id === selectedId) || null,
    [scenarios, selectedId],
  );

  const scenarioRuns = useMemo(
    () => runs.filter((run) => !selectedId || run.scenario_id === selectedId),
    [runs, selectedId],
  );

  const compareCandidates = useMemo(
    () => scenarioRuns.filter((run) => run.status === "completed" && run.id !== activeRun?.id && run.result),
    [scenarioRuns, activeRun],
  );

  const compareRun = useMemo(
    () => compareCandidates.find((run) => run.id === compareRunId) || null,
    [compareCandidates, compareRunId],
  );

  function updateConfig(mutator: (draft: ScenarioConfig) => void) {
    setConfig((current) => {
      if (!current) {
        return current;
      }
      const next = clone(current);
      mutator(next);
      return next;
    });
  }

  async function handleSave() {
    if (!config || !selectedId) {
      return;
    }
    setBusy(true);
    try {
      const saved = await saveScenario(selectedId, config);
      setScenarios((current) => current.map((scenario) => (scenario.id === saved.id ? saved : scenario)));
      setConfig(clone(saved.config));
      setMessage("Scenario saved.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveAsNew() {
    if (!config) {
      return;
    }
    setBusy(true);
    try {
      const created = await createScenario(config);
      setScenarios((current) => [created, ...current]);
      setSelectedId(created.id);
      setConfig(clone(created.config));
      setMessage("Scenario duplicated.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    if (!config || !selectedId) {
      return;
    }
    setBusy(true);
    try {
      await saveScenario(selectedId, config);
      const run = await createRun(selectedId);
      setActiveRun(run);
      setRuns((current) => [run, ...current.filter((existing) => existing.id !== run.id)]);
      setCompareRunId("");
      setActiveTab("overview");
      setMessage("Run launched.");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const result = activeRun?.result;
  const compareSummary = compareRun?.result?.summary ?? null;

  return (
    <div className="shell">
      <header className="masthead">
        <div>
          <p className="eyebrow">Port Decision Support</p>
          <h1>Terminal Sandbox</h1>
          <p className="lede">
            A modern import/export simulation workspace for testing how shared resources, yard fill,
            rail service, and export cutoffs change terminal performance.
          </p>
        </div>
        <div className="status-chip">{message}</div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="panel">
            <div className="panel-header">
              <h3>Scenario Library</h3>
              <button className="ghost-button" onClick={() => void refreshScenarios()}>
                Refresh
              </button>
            </div>
            <div className="scenario-list">
              {scenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  className={`scenario-card ${selectedId === scenario.id ? "active" : ""}`}
                  onClick={() => {
                    setSelectedId(scenario.id);
                    setConfig(clone(scenario.config));
                    setCompareRunId("");
                  }}
                >
                  <strong>{scenario.config.name}</strong>
                  <span>{scenario.id}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Run History</h3>
              <button className="ghost-button" onClick={() => void refreshRuns()}>
                Refresh
              </button>
            </div>
            <div className="run-list">
              {scenarioRuns.slice(0, 8).map((run) => (
                <button
                  key={run.id}
                  className={`scenario-card ${activeRun?.id === run.id ? "active" : ""}`}
                  onClick={() => setActiveRun(run)}
                >
                  <strong>{run.id}</strong>
                  <span>
                    {run.status} · {new Date(run.created_at).toLocaleString()}
                  </span>
                </button>
              ))}
              {!scenarioRuns.length && <p className="helper-copy">Run history will appear here.</p>}
            </div>
          </div>

          {config && (
            <div className="panel builder-panel">
              <div className="panel-header">
                <h3>Scenario Builder</h3>
                <span>{selectedScenario?.id}</span>
              </div>

              <label>
                Name
                <input
                  className="field"
                  value={config.name}
                  onChange={(event) => updateConfig((draft) => (draft.name = event.target.value))}
                />
              </label>
              <label>
                Description
                <textarea
                  className="field field-textarea"
                  value={config.description}
                  onChange={(event) => updateConfig((draft) => (draft.description = event.target.value))}
                />
              </label>

              <div className="field-grid">
                <label>
                  Horizon (hrs)
                  {numberInput(
                    config.horizon_hours,
                    (value) => updateConfig((draft) => (draft.horizon_hours = value)),
                    1,
                    1,
                  )}
                </label>
                <label>
                  Drain (hrs)
                  {numberInput(
                    config.drain_hours,
                    (value) => updateConfig((draft) => (draft.drain_hours = value)),
                    1,
                    0,
                  )}
                </label>
                <label>
                  Seed
                  {numberInput(
                    config.random_seed,
                    (value) => updateConfig((draft) => (draft.random_seed = value)),
                    1,
                  )}
                </label>
              </div>

              <details open>
                <summary>Shared Resources</summary>
                <div className="field-grid">
                  <label>
                    Berths
                    {numberInput(
                      config.resources.berths,
                      (value) => updateConfig((draft) => (draft.resources.berths = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    STS Cranes
                    {numberInput(
                      config.resources.sts_cranes,
                      (value) => updateConfig((draft) => (draft.resources.sts_cranes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Yard Equipment
                    {numberInput(
                      config.resources.yard_equipment,
                      (value) => updateConfig((draft) => (draft.resources.yard_equipment = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Gate Lanes
                    {numberInput(
                      config.resources.gate_lanes,
                      (value) => updateConfig((draft) => (draft.resources.gate_lanes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Rail Slots
                    {numberInput(
                      config.resources.rail_slots,
                      (value) => updateConfig((draft) => (draft.resources.rail_slots = value)),
                      1,
                      1,
                    )}
                  </label>
                </div>
              </details>

              <details>
                <summary>Gate, Rail, Stacking</summary>
                <div className="field-grid">
                  <label>
                    Gate Open
                    {numberInput(
                      config.gate_calendar.open_hour,
                      (value) => updateConfig((draft) => (draft.gate_calendar.open_hour = value)),
                      1,
                      0,
                      23,
                    )}
                  </label>
                  <label>
                    Gate Close
                    {numberInput(
                      config.gate_calendar.close_hour,
                      (value) => updateConfig((draft) => (draft.gate_calendar.close_hour = value)),
                      1,
                      1,
                      24,
                    )}
                  </label>
                  <label>
                    Import Trains / Day
                    {numberInput(
                      config.rail.import_departures_per_day,
                      (value) => updateConfig((draft) => (draft.rail.import_departures_per_day = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Train Capacity
                    {numberInput(
                      config.rail.train_capacity,
                      (value) => updateConfig((draft) => (draft.rail.train_capacity = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Train Load Minutes
                    {numberInput(
                      config.rail.train_load_minutes,
                      (value) => updateConfig((draft) => (draft.rail.train_load_minutes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Putaway Minutes
                    {numberInput(
                      config.yard_policy.putaway_minutes,
                      (value) => updateConfig((draft) => (draft.yard_policy.putaway_minutes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Prestage Minutes
                    {numberInput(
                      config.yard_policy.prestage_minutes,
                      (value) => updateConfig((draft) => (draft.yard_policy.prestage_minutes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Retrieve Minutes
                    {numberInput(
                      config.yard_policy.base_retrieve_minutes,
                      (value) => updateConfig((draft) => (draft.yard_policy.base_retrieve_minutes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Reshuffle Minutes
                    {numberInput(
                      config.yard_policy.reshuffle_minutes,
                      (value) => updateConfig((draft) => (draft.yard_policy.reshuffle_minutes = value)),
                      1,
                      1,
                    )}
                  </label>
                  <label>
                    Putaway Alpha
                    {numberInput(
                      config.yard_policy.alpha_putaway,
                      (value) => updateConfig((draft) => (draft.yard_policy.alpha_putaway = value)),
                      0.05,
                      0,
                    )}
                  </label>
                  <label>
                    Retrieval Beta
                    {numberInput(
                      config.yard_policy.beta_retrieval,
                      (value) => updateConfig((draft) => (draft.yard_policy.beta_retrieval = value)),
                      0.05,
                      0,
                    )}
                  </label>
                  <label>
                    Congestion Threshold
                    {numberInput(
                      config.yard_policy.congestion_threshold,
                      (value) => updateConfig((draft) => (draft.yard_policy.congestion_threshold = value)),
                      0.05,
                      0,
                      1,
                    )}
                  </label>
                </div>
              </details>

              <details>
                <summary>Yard Blocks</summary>
                <div className="stack">
                  {config.yard_blocks.map((block, index) => (
                    <div key={block.id} className="mini-card">
                      <h4>{block.label}</h4>
                      <div className="field-grid">
                        <label>
                          Capacity
                          {numberInput(block.capacity_teu, (value) =>
                            updateConfig((draft) => (draft.yard_blocks[index].capacity_teu = value)),
                          )}
                        </label>
                        <label>
                          Max Stack
                          {numberInput(block.max_stack_height, (value) =>
                            updateConfig((draft) => (draft.yard_blocks[index].max_stack_height = value)),
                          )}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </details>

              <details>
                <summary>Container Types</summary>
                <div className="stack">
                  {config.container_types.map((type, index) => (
                    <div key={type.id} className="mini-card">
                      <h4>{type.label}</h4>
                      <div className="field-grid">
                        <label>
                          Initial Imports
                          {numberInput(type.initial_import_units, (value) =>
                            updateConfig((draft) => (draft.container_types[index].initial_import_units = value)),
                          )}
                        </label>
                        <label>
                          Initial Exports
                          {numberInput(type.initial_export_ready_units, (value) =>
                            updateConfig(
                              (draft) => (draft.container_types[index].initial_export_ready_units = value),
                            ),
                          )}
                        </label>
                        <label>
                          Import Truck Share
                          {numberInput(
                            type.import_truck_share,
                            (value) =>
                              updateConfig((draft) => (draft.container_types[index].import_truck_share = value)),
                            0.05,
                            0,
                            1,
                          )}
                        </label>
                        <label>
                          Export Truck Share
                          {numberInput(
                            type.export_truck_share,
                            (value) =>
                              updateConfig((draft) => (draft.container_types[index].export_truck_share = value)),
                            0.05,
                            0,
                            1,
                          )}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </details>

              <details>
                <summary>Vessel Calls</summary>
                <div className="stack">
                  {config.vessel_calls.map((vessel, index) => (
                    <div key={vessel.id} className="mini-card">
                      <h4>{vessel.name}</h4>
                      <div className="field-grid">
                        <label>
                          ETA Hour
                          {numberInput(vessel.eta_hour, (value) =>
                            updateConfig((draft) => (draft.vessel_calls[index].eta_hour = value)),
                          )}
                        </label>
                        <label>
                          Export Cutoff
                          {numberInput(vessel.export_cutoff_hours_before_eta, (value) =>
                            updateConfig(
                              (draft) => (draft.vessel_calls[index].export_cutoff_hours_before_eta = value),
                            ),
                          )}
                        </label>
                        <label>
                          Prestage Window
                          {numberInput(vessel.prestage_hours_before_eta, (value) =>
                            updateConfig((draft) => (draft.vessel_calls[index].prestage_hours_before_eta = value)),
                          )}
                        </label>
                        <label>
                          Load Cutoff
                          {numberInput(vessel.load_cutoff_hours_after_eta, (value) =>
                            updateConfig((draft) => (draft.vessel_calls[index].load_cutoff_hours_after_eta = value)),
                          )}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </details>

              <div className="action-row">
                <button className="ghost-button" disabled={busy} onClick={() => void handleSaveAsNew()}>
                  Save As New
                </button>
                <button className="ghost-button" disabled={busy} onClick={() => void handleSave()}>
                  Save
                </button>
                <button className="primary-button" disabled={busy} onClick={() => void handleRun()}>
                  Run Scenario
                </button>
              </div>
            </div>
          )}
        </aside>

        <main className="content">
          <div className="content-toolbar">
            <div className="tab-strip">
              {(["overview", "yard", "vessels", "containers"] as TabKey[]).map((tab) => (
                <button
                  key={tab}
                  className={`tab-button ${activeTab === tab ? "active" : ""}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="toolbar-cluster">
              <label className="compare-picker">
                Compare Against
                <select
                  className="field"
                  value={compareRunId}
                  onChange={(event) => setCompareRunId(event.target.value)}
                >
                  <option value="">No baseline</option>
                  {compareCandidates.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.id}
                    </option>
                  ))}
                </select>
              </label>
              {activeRun && (
                <div className="run-pill">
                  <strong>{activeRun.id}</strong>
                  <span>{activeRun.status}</span>
                  <span>{Math.round(activeRun.progress * 100)}%</span>
                </div>
              )}
            </div>
          </div>

          {!result && (
            <div className="empty-state">
              <h2>Run a scenario to populate the workspace</h2>
              <p>
                The builder on the left controls shared berths, cranes, yard equipment, gates,
                rail departures, and fill-based stacking effects for both imports and exports.
              </p>
            </div>
          )}

          {result && activeTab === "overview" && (
            <>
              <div className="stats-grid">
                <StatCard
                  label="Import Completed"
                  value={String(metric(result.summary, "import_completed"))}
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "import_completed") -
                            metric(compareSummary, "import_completed"),
                          0,
                        )} vs baseline`
                      : null
                  }
                />
                <StatCard
                  label="Export Loaded"
                  value={String(metric(result.summary, "export_loaded"))}
                  accent="#0f766e"
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "export_loaded") - metric(compareSummary, "export_loaded"),
                          0,
                        )} vs baseline`
                      : null
                  }
                />
                <StatCard
                  label="Export Rolled"
                  value={String(metric(result.summary, "export_rolled"))}
                  accent="#b45309"
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "export_rolled") - metric(compareSummary, "export_rolled"),
                          0,
                        )} vs baseline`
                      : null
                  }
                />
                <StatCard
                  label="Peak Yard"
                  value={String(metric(result.summary, "peak_yard_units"))}
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "peak_yard_units") - metric(compareSummary, "peak_yard_units"),
                          0,
                        )} vs baseline`
                      : null
                  }
                />
                <StatCard
                  label="Avg Import Dwell"
                  value={`${metric(result.summary, "avg_import_dwell_hours")} h`}
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "avg_import_dwell_hours") -
                            metric(compareSummary, "avg_import_dwell_hours"),
                        )} h vs baseline`
                      : null
                  }
                />
                <StatCard
                  label="Avg Export Dwell"
                  value={`${metric(result.summary, "avg_export_dwell_hours")} h`}
                  delta={
                    compareSummary
                      ? `${formatDelta(
                          metric(result.summary, "avg_export_dwell_hours") -
                            metric(compareSummary, "avg_export_dwell_hours"),
                        )} h vs baseline`
                      : null
                  }
                />
              </div>

              <div className="compare-banner">
                <div>
                  <strong>Shared-resource logic</strong>
                  <p>
                    Imports and exports compete for the same berth, STS, yard, gate, and rail
                    resources. Yard fill increases putaway and retrieval time through stacking
                    logic and burial depth.
                  </p>
                </div>
                {compareRun && (
                  <div className="compare-chip">
                    Baseline {compareRun.id} selected for KPI deltas and chart inspection.
                  </div>
                )}
              </div>

              <div className="chart-grid">
                <LineCard
                  title="Yard Occupancy"
                  data={result.timeseries}
                  keys={[
                    { key: "total_yard_units", color: "#1d4ed8", label: "Total" },
                    { key: "import_yard_units", color: "#0f766e", label: "Import" },
                    { key: "export_yard_units", color: "#b45309", label: "Export" },
                  ]}
                />
                <LineCard
                  title="Queues"
                  data={result.timeseries}
                  keys={[
                    { key: "berth_queue", color: "#173b67", label: "Berth" },
                    { key: "gate_queue", color: "#f97316", label: "Gate" },
                    { key: "yard_queue", color: "#334155", label: "Yard" },
                  ]}
                />
                <LineCard
                  title="Rail Pressure"
                  data={result.timeseries}
                  keys={[
                    { key: "rail_queue", color: "#14b8a6", label: "Rail" },
                    { key: "export_yard_units", color: "#b45309", label: "Export Yard" },
                  ]}
                />
                <LineCard
                  title="Resource Utilization"
                  data={result.timeseries}
                  keys={[
                    { key: "sts_utilization", color: "#7c3aed", label: "STS" },
                    { key: "gate_utilization", color: "#0ea5e9", label: "Gate" },
                    { key: "yard_utilization", color: "#16a34a", label: "Yard" },
                  ]}
                />
              </div>
            </>
          )}

          {result && activeTab === "yard" && (
            <div className="chart-grid">
              <LineCard
                title="Yard Mix"
                data={result.timeseries}
                keys={[
                  { key: "import_yard_units", color: "#0f766e", label: "Import Yard" },
                  { key: "export_yard_units", color: "#b45309", label: "Export Yard" },
                  { key: "total_yard_units", color: "#173b67", label: "Total Yard" },
                ]}
              />
              <div className="panel">
                <div className="panel-header">
                  <h3>Operational Notes</h3>
                </div>
                <ul className="note-list">
                  <li>Putaway time rises with fill rate using a quadratic congestion factor.</li>
                  <li>Burial depth is assigned at yard-in and turns into reshuffle time later.</li>
                  <li>Export prestage removes boxes from the yard into a quay-ready buffer.</li>
                  <li>Imports cannot leave the yard until the business release timer expires.</li>
                </ul>
              </div>
            </div>
          )}

          {result && activeTab === "vessels" && (
            <div className="panel">
              <div className="panel-header">
                <h3>Vessel Calls</h3>
              </div>
              <div className="table-shell">
                <table>
                  <thead>
                    <tr>
                      <th>Vessel</th>
                      <th>ETA</th>
                      <th>ATA</th>
                      <th>Berth Start</th>
                      <th>Departure</th>
                      <th>Status</th>
                      <th>Imports</th>
                      <th>Exports Loaded</th>
                      <th>Rolled</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.vessels.map((vessel) => (
                      <tr key={String(vessel.id)}>
                        <td>{String(vessel.name)}</td>
                        <td>{String(vessel.eta_hour)}</td>
                        <td>{String(vessel.ata_hour)}</td>
                        <td>{String(vessel.berth_start_hour ?? "-")}</td>
                        <td>{String(vessel.departure_hour ?? "-")}</td>
                        <td>{String(vessel.status)}</td>
                        <td>{String(vessel.imports)}</td>
                        <td>{String(vessel.loaded_exports)}</td>
                        <td>{String(vessel.rolled_exports)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result && activeTab === "containers" && (
            <div className="panel">
              <div className="panel-header">
                <h3>Container Records</h3>
                <span>{result.containers.length} rows</span>
              </div>
              <div className="table-shell">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Direction</th>
                      <th>Type</th>
                      <th>Mode</th>
                      <th>Status</th>
                      <th>Target Vessel</th>
                      <th>Yard In</th>
                      <th>Exit / Load</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.containers.slice(0, 200).map((container) => (
                      <tr key={String(container.id)}>
                        <td>{String(container.id)}</td>
                        <td>{String(container.direction)}</td>
                        <td>{String(container.type)}</td>
                        <td>{String(container.mode)}</td>
                        <td>{String(container.status)}</td>
                        <td>{String(container.target_vessel_id ?? "-")}</td>
                        <td>{String(container.yard_in ?? "-")}</td>
                        <td>{String(container.terminal_exit ?? container.loaded_on_vessel ?? "-")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
