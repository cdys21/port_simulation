import { useEffect, useMemo, useState } from "react";

import {
  PlaybackBlock,
  PlaybackEvent,
  PlaybackSnapshot,
  PlaybackVessel,
  RunResult,
} from "./types";

type PlaybackTabProps = {
  result: RunResult;
};

type ChartKey = {
  key: string;
  color: string;
  label: string;
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function formatHour(hour: number): string {
  const totalMinutes = Math.max(0, Math.round(hour * 60));
  const day = Math.floor(totalMinutes / (24 * 60));
  const remainder = totalMinutes % (24 * 60);
  const hh = String(Math.floor(remainder / 60)).padStart(2, "0");
  const mm = String(remainder % 60).padStart(2, "0");
  return `D${day} ${hh}:${mm}`;
}

function polylineTimePoints(
  data: Array<Record<string, number>>,
  key: string,
  width: number,
  height: number,
  maxHour: number,
): string {
  if (!data.length) {
    return "";
  }
  const values = data.map((point) => point[key] ?? 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return data
    .map((point) => {
      const x = ((point.hour ?? 0) / Math.max(maxHour, 0.01)) * width;
      const y = height - (((point[key] ?? 0) - min) / span) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

function findSnapshotAtHour(snapshots: PlaybackSnapshot[], hour: number): PlaybackSnapshot {
  let current = snapshots[0];
  for (const snapshot of snapshots) {
    if (snapshot.hour <= hour) {
      current = snapshot;
    } else {
      break;
    }
  }
  return current;
}

function severityClass(severity: string): string {
  if (severity === "warning") {
    return "warning";
  }
  return "info";
}

function fillColor(fillRate: number): string {
  if (fillRate >= 0.9) {
    return "#b45309";
  }
  if (fillRate >= 0.72) {
    return "#f97316";
  }
  if (fillRate >= 0.5) {
    return "#0f766e";
  }
  return "#1d4ed8";
}

function vesselTone(vessel: PlaybackVessel): string {
  if (vessel.status === "departed") {
    return "#94a3b8";
  }
  if (vessel.zone.startsWith("berth")) {
    return vessel.phase === "load" ? "#0f766e" : "#173b67";
  }
  if (vessel.zone === "anchorage") {
    return "#f97316";
  }
  return "#64748b";
}

function flowTokenCount(count: number): number {
  if (count <= 0) {
    return 0;
  }
  return clamp(Math.ceil(Math.sqrt(count)), 1, 6);
}

function flowFraction(currentHour: number, index: number, total: number, cycleMinutes: number): number {
  const base = (currentHour * 60) / cycleMinutes;
  return (base + index / Math.max(total, 1)) % 1;
}

function bottleneckLabel(snapshot: PlaybackSnapshot): string {
  const candidates = [
    { label: "Berth", value: snapshot.queues.berth_queue + snapshot.resources.berth_utilization * 5 },
    { label: "Gate", value: snapshot.queues.gate_queue + snapshot.resources.gate_utilization * 5 },
    { label: "Yard", value: snapshot.queues.yard_queue + snapshot.resources.yard_utilization * 5 },
    { label: "Rail", value: snapshot.queues.rail_queue + snapshot.resources.rail_utilization * 5 },
  ];
  candidates.sort((left, right) => right.value - left.value);
  return candidates[0]?.label ?? "Balanced";
}

function PlaybackLineCard({
  title,
  data,
  keys,
  cursorHour,
  maxHour,
  onSeek,
}: {
  title: string;
  data: Array<Record<string, number>>;
  keys: ChartKey[];
  cursorHour: number;
  maxHour: number;
  onSeek: (hour: number) => void;
}) {
  const width = 420;
  const height = 140;
  const cursorX = (cursorHour / Math.max(maxHour, 0.01)) * width;

  return (
    <div className="panel chart-card playback-chart-card">
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
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart-svg interactive"
        onClick={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          const ratio = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
          onSeek(ratio * maxHour);
        }}
      >
        <rect x="0" y="0" width={width} height={height} rx="12" className="chart-bg" />
        {keys.map((entry) => (
          <polyline
            key={entry.key}
            fill="none"
            stroke={entry.color}
            strokeWidth="3"
            points={polylineTimePoints(data, entry.key, width, height, maxHour)}
          />
        ))}
        <line x1={cursorX} y1="0" x2={cursorX} y2={height} className="chart-cursor" />
      </svg>
    </div>
  );
}

function FlowDots({
  start,
  end,
  count,
  color,
  currentHour,
  label,
  cycleMinutes = 24,
}: {
  start: [number, number];
  end: [number, number];
  count: number;
  color: string;
  currentHour: number;
  label: string;
  cycleMinutes?: number;
}) {
  const dots = flowTokenCount(count);
  const [x1, y1] = start;
  const [x2, y2] = end;

  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="4" strokeOpacity="0.22" />
      {Array.from({ length: dots }).map((_, index) => {
        const fraction = flowFraction(currentHour, index, dots, cycleMinutes);
        const x = x1 + (x2 - x1) * fraction;
        const y = y1 + (y2 - y1) * fraction;
        return <circle key={`${label}-${index}`} cx={x} cy={y} r="6" fill={color} fillOpacity="0.95" />;
      })}
      {count > 0 && (
        <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 12} className="svg-label" textAnchor="middle">
          {label}: {count}
        </text>
      )}
    </g>
  );
}

function YardBlockCard({ block, x, y }: { block: PlaybackBlock; x: number; y: number }) {
  const width = 148;
  const height = 76;
  const fillWidth = width * clamp(block.fill_rate, 0, 1);
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx="16" fill="#ffffff" fillOpacity="0.92" />
      <rect x={x + 10} y={y + 40} width={width - 20} height="14" rx="7" fill="#e2e8f0" />
      <rect x={x + 10} y={y + 40} width={Math.max(0, fillWidth - 20)} height="14" rx="7" fill={fillColor(block.fill_rate)} />
      <text x={x + 12} y={y + 22} className="svg-title">
        {block.label}
      </text>
      <text x={x + 12} y={y + 34} className="svg-label">
        {block.occupancy}/{block.capacity} TEU
      </text>
      <text x={x + width - 12} y={y + 34} className="svg-label" textAnchor="end">
        {Math.round(block.fill_rate * 100)}%
      </text>
    </g>
  );
}

function TerminalPlaybackMap({
  snapshot,
  currentHour,
}: {
  snapshot: PlaybackSnapshot;
  currentHour: number;
}) {
  const berthed = snapshot.vessels.filter((vessel) => vessel.zone.startsWith("berth"));
  const anchorage = snapshot.vessels.filter((vessel) => vessel.zone === "anchorage");
  const blockPositions: Array<[number, number]> = [
    [330, 105],
    [330, 205],
    [330, 305],
  ];

  return (
    <div className="panel playback-stage">
      <div className="panel-header">
        <h3>Terminal Playback</h3>
        <span>{snapshot.gate_open ? "Gate open" : "Gate closed"}</span>
      </div>
      <svg viewBox="0 0 860 470" className="playback-map">
        <rect x="0" y="0" width="860" height="470" rx="26" fill="#f8fafc" />
        <rect x="20" y="45" width="150" height="380" rx="26" fill="#dbeafe" />
        <rect x="178" y="45" width="86" height="380" rx="20" fill="#cbd5e1" />
        <rect x="295" y="78" width="290" height="302" rx="28" fill="#e2e8f0" />
        <rect x="625" y="82" width="186" height="114" rx="24" fill="#fef3c7" />
        <rect x="625" y="250" width="186" height="112" rx="24" fill="#d1fae5" />

        <text x="34" y="72" className="svg-zone-title">
          Anchorage
        </text>
        <text x="198" y="72" className="svg-zone-title">
          Quay
        </text>
        <text x="316" y="72" className="svg-zone-title">
          Yard
        </text>
        <text x="646" y="106" className="svg-zone-title">
          Gate
        </text>
        <text x="646" y="274" className="svg-zone-title">
          Rail
        </text>

        {Array.from({ length: snapshot.resources.berths_capacity }).map((_, index) => {
          const berthY = 110 + index * 105;
          return (
            <g key={`berth-${index + 1}`}>
              <line x1="178" y1={berthY} x2="264" y2={berthY} className="berth-line" />
              <text x="186" y={berthY - 10} className="svg-label">
                Berth {index + 1}
              </text>
            </g>
          );
        })}

        {anchorage.map((vessel, index) => (
          <g key={vessel.id}>
            <rect
              x={40}
              y={104 + index * 72}
              width="102"
              height="42"
              rx="14"
              fill={vesselTone(vessel)}
              fillOpacity="0.9"
            />
            <text x="51" y={129 + index * 72} className="svg-ship-label">
              {vessel.name}
            </text>
          </g>
        ))}

        {berthed.map((vessel) => {
          const berthIndex = Number(vessel.zone.replace("berth-", "")) - 1;
          const y = 88 + berthIndex * 105;
          return (
            <g key={vessel.id}>
              <rect x="92" y={y} width="116" height="46" rx="16" fill={vesselTone(vessel)} />
              <text x="104" y={y + 20} className="svg-ship-label">
                {vessel.name}
              </text>
              <text x="104" y={y + 34} className="svg-label light">
                {vessel.phase} | I:{vessel.remaining_imports} E:{vessel.remaining_exports}
              </text>
            </g>
          );
        })}

        {snapshot.blocks.map((block, index) => {
          const [x, y] = blockPositions[index] ?? [330, 105 + index * 100];
          return <YardBlockCard key={block.id} block={block} x={x} y={y} />;
        })}

        <FlowDots
          start={[236, 135]}
          end={[328, 155]}
          count={snapshot.flows.vessel_to_yard}
          color="#1d4ed8"
          currentHour={currentHour}
          label="Discharge"
        />
        <FlowDots
          start={[332, 246]}
          end={[236, 246]}
          count={snapshot.flows.quay_to_vessel}
          color="#0f766e"
          currentHour={currentHour}
          label="Load"
        />
        <FlowDots
          start={[566, 134]}
          end={[642, 134]}
          count={snapshot.flows.yard_to_gate}
          color="#f97316"
          currentHour={currentHour}
          label="Import Out"
        />
        <FlowDots
          start={[642, 160]}
          end={[566, 160]}
          count={snapshot.flows.gate_to_yard}
          color="#c2410c"
          currentHour={currentHour}
          label="Export In"
        />
        <FlowDots
          start={[566, 303]}
          end={[642, 303]}
          count={snapshot.flows.yard_to_rail}
          color="#0ea5e9"
          currentHour={currentHour}
          label="Rail Out"
          cycleMinutes={18}
        />
        <FlowDots
          start={[642, 332]}
          end={[566, 332]}
          count={snapshot.flows.rail_to_yard}
          color="#14b8a6"
          currentHour={currentHour}
          label="Rail In"
          cycleMinutes={18}
        />
        <FlowDots
          start={[334, 280]}
          end={[236, 280]}
          count={snapshot.flows.yard_to_quay}
          color="#7c3aed"
          currentHour={currentHour}
          label="Prestage"
          cycleMinutes={20}
        />
        <FlowDots
          start={[445, 355]}
          end={[445, 260]}
          count={snapshot.flows.yard_retrieval}
          color="#334155"
          currentHour={currentHour}
          label="Retrieve"
          cycleMinutes={22}
        />

        <g>
          <circle cx="694" cy="118" r="10" fill={snapshot.gate_open ? "#16a34a" : "#94a3b8"} />
          <text x="714" y="122" className="svg-label">
            {snapshot.gate_open ? "Open" : "Closed"}
          </text>
        </g>

        <g>
          <rect x="648" y="122" width="128" height="44" rx="16" className="queue-pill" />
          <text x="662" y="140" className="svg-label">
            Gate Queue
          </text>
          <text x="662" y="156" className="svg-title">
            {snapshot.queues.gate_queue}
          </text>
        </g>

        <g>
          <rect x="648" y="286" width="128" height="44" rx="16" className="queue-pill" />
          <text x="662" y="304" className="svg-label">
            Rail Queue
          </text>
          <text x="662" y="320" className="svg-title">
            {snapshot.queues.rail_queue}
          </text>
        </g>

        <g>
          <rect x="46" y="350" width="112" height="52" rx="18" className="queue-pill" />
          <text x="60" y="370" className="svg-label">
            Berth Queue
          </text>
          <text x="60" y="390" className="svg-title">
            {snapshot.queues.berth_queue}
          </text>
        </g>

        <g>
          <rect x="600" y="396" width="222" height="42" rx="18" className="queue-pill dark" />
          <text x="618" y="421" className="svg-label light">
            Bottleneck now: {bottleneckLabel(snapshot)}
          </text>
        </g>
      </svg>
    </div>
  );
}

export default function PlaybackTab({ result }: PlaybackTabProps) {
  const [playbackHour, setPlaybackHour] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const playback = result.playback ?? null;
  const snapshots = playback?.snapshots ?? [];
  const events = playback?.events ?? [];
  const snapshotStep = (playback?.snapshot_interval_minutes ?? 15) / 60;
  const maxHour = playback?.duration_hours || snapshots[snapshots.length - 1]?.hour || 0;

  useEffect(() => {
    setPlaybackHour(0);
    setIsPlaying(false);
  }, [result]);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    let frame = 0;
    let lastTick = performance.now();
    const tick = (timestamp: number) => {
      const deltaSeconds = (timestamp - lastTick) / 1000;
      lastTick = timestamp;
      setPlaybackHour((current) => {
        const next = current + deltaSeconds * speed;
        if (next >= maxHour) {
          setIsPlaying(false);
          return maxHour;
        }
        return next;
      });
      frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [isPlaying, maxHour, speed]);

  const currentSnapshot = useMemo(
    () => (snapshots.length ? findSnapshotAtHour(snapshots, playbackHour) : null),
    [snapshots, playbackHour],
  );

  const chartData = useMemo(
    () =>
      snapshots.map((snapshot) => ({
        hour: snapshot.hour,
        total_yard_units: snapshot.yard.total_units,
        import_yard_units: snapshot.yard.import_units,
        export_yard_units: snapshot.yard.export_units,
        berth_queue: snapshot.queues.berth_queue,
        gate_queue: snapshot.queues.gate_queue,
        rail_queue: snapshot.queues.rail_queue,
        yard_queue: snapshot.queues.yard_queue,
        sts_utilization: snapshot.resources.sts_utilization,
        gate_utilization: snapshot.resources.gate_utilization,
        yard_utilization: snapshot.resources.yard_utilization,
        rail_utilization: snapshot.resources.rail_utilization,
      })),
    [snapshots],
  );

  const bookmarkEvents = useMemo(
    () =>
      events.filter((event) =>
        [
          "vessel_berthed",
          "vessel_switch_over",
          "load_window_open",
          "vessel_departed",
          "import_train_departed",
          "yard_congested",
          "gate_queue_spike",
          "export_rolled",
        ].includes(event.kind),
      ),
    [events],
  );

  const recentEvents = useMemo(
    () =>
      events
        .filter((event) => event.hour <= playbackHour)
        .slice(-6)
        .reverse(),
    [events, playbackHour],
  );

  const upcomingEvents = useMemo(
    () => events.filter((event) => event.hour > playbackHour).slice(0, 4),
    [events, playbackHour],
  );

  if (!playback || !snapshots.length || !currentSnapshot) {
    return (
      <div className="panel empty-state">
        <h2>Playback is not available for this run</h2>
        <p>Replay data is generated for newer runs. Rerun the scenario to populate the playback workspace.</p>
      </div>
    );
  }

  return (
    <div className="playback-shell">
      <div className="panel playback-toolbar">
        <div>
          <p className="eyebrow">Playback</p>
          <h2>Operations Replay</h2>
        </div>
        <div className="transport-row">
          <button className="ghost-button" onClick={() => setPlaybackHour((current) => Math.max(0, current - 1))}>
            -1h
          </button>
          <button className="ghost-button" onClick={() => setPlaybackHour((current) => Math.max(0, current - 0.25))}>
            -15m
          </button>
          <button className="primary-button" onClick={() => setIsPlaying((current) => !current)}>
            {isPlaying ? "Pause" : "Play"}
          </button>
          <button
            className="ghost-button"
            onClick={() => setPlaybackHour((current) => Math.min(maxHour, current + 0.25))}
          >
            +15m
          </button>
          <button className="ghost-button" onClick={() => setPlaybackHour((current) => Math.min(maxHour, current + 1))}>
            +1h
          </button>
        </div>
      </div>

      <div className="panel timeline-shell">
        <div className="timeline-meta">
          <strong>{formatHour(playbackHour)}</strong>
          <span>Snapshot every {playback.snapshot_interval_minutes} minutes</span>
        </div>
        <div className="speed-row">
          {[0.25, 1, 4, 12].map((value) => (
            <button
              key={value}
              className={`tab-button ${speed === value ? "active" : ""}`}
              onClick={() => setSpeed(value)}
            >
              {value < 1 ? "15m/s" : `${value}h/s`}
            </button>
          ))}
        </div>
        <div className="timeline-track">
          {bookmarkEvents.map((event) => (
            <button
              key={`${event.kind}-${event.hour}-${event.entity_id ?? "none"}`}
              className={`timeline-marker ${severityClass(event.severity)}`}
              style={{ left: `${(event.hour / Math.max(maxHour, 0.01)) * 100}%` }}
              onClick={() => setPlaybackHour(event.hour)}
              title={`${formatHour(event.hour)} - ${event.label}`}
            />
          ))}
          <div className="timeline-cursor" style={{ left: `${(playbackHour / Math.max(maxHour, 0.01)) * 100}%` }} />
        </div>
        <input
          className="timeline-slider"
          type="range"
          min={0}
          max={maxHour}
          step={snapshotStep}
          value={playbackHour}
          onChange={(event) => setPlaybackHour(Number(event.target.value))}
        />
      </div>

      <div className="playback-layout">
        <TerminalPlaybackMap snapshot={currentSnapshot} currentHour={playbackHour} />

        <div className="playback-sidebar">
          <div className="panel">
            <div className="panel-header">
              <h3>Current State</h3>
            </div>
            <div className="stats-grid compact">
              <div className="stat-card">
                <span>Yard Fill</span>
                <strong>{Math.round(currentSnapshot.yard.fill_rate * 100)}%</strong>
                <small>{currentSnapshot.yard.total_units} units in yard</small>
              </div>
              <div className="stat-card">
                <span>STS Utilization</span>
                <strong>{Math.round(currentSnapshot.resources.sts_utilization * 100)}%</strong>
                <small>{currentSnapshot.resources.berths_in_use}/{currentSnapshot.resources.berths_capacity} berths busy</small>
              </div>
              <div className="stat-card">
                <span>Exports Rolled</span>
                <strong>{currentSnapshot.counters.export_rolled}</strong>
                <small>cumulative</small>
              </div>
              <div className="stat-card">
                <span>Bottleneck</span>
                <strong>{bottleneckLabel(currentSnapshot)}</strong>
                <small>derived from queue and utilization pressure</small>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Recent Events</h3>
            </div>
            <div className="event-list">
              {recentEvents.map((event: PlaybackEvent) => (
                <button
                  key={`${event.kind}-${event.hour}-${event.entity_id ?? "recent"}`}
                  className={`event-card ${severityClass(event.severity)}`}
                  onClick={() => setPlaybackHour(event.hour)}
                >
                  <strong>{formatHour(event.hour)}</strong>
                  <span>{event.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h3>Upcoming Bookmarks</h3>
            </div>
            <div className="event-list">
              {upcomingEvents.map((event: PlaybackEvent) => (
                <button
                  key={`${event.kind}-${event.hour}-${event.entity_id ?? "upcoming"}`}
                  className={`event-card ${severityClass(event.severity)}`}
                  onClick={() => setPlaybackHour(event.hour)}
                >
                  <strong>{formatHour(event.hour)}</strong>
                  <span>{event.label}</span>
                </button>
              ))}
              {!upcomingEvents.length && <p className="helper-copy">No later events in this run.</p>}
            </div>
          </div>
        </div>
      </div>

      <div className="chart-grid">
        <PlaybackLineCard
          title="Yard Occupancy"
          data={chartData}
          keys={[
            { key: "total_yard_units", color: "#1d4ed8", label: "Total" },
            { key: "import_yard_units", color: "#0f766e", label: "Import" },
            { key: "export_yard_units", color: "#b45309", label: "Export" },
          ]}
          cursorHour={playbackHour}
          maxHour={maxHour}
          onSeek={setPlaybackHour}
        />
        <PlaybackLineCard
          title="Queues"
          data={chartData}
          keys={[
            { key: "berth_queue", color: "#173b67", label: "Berth" },
            { key: "gate_queue", color: "#f97316", label: "Gate" },
            { key: "rail_queue", color: "#14b8a6", label: "Rail" },
            { key: "yard_queue", color: "#334155", label: "Yard" },
          ]}
          cursorHour={playbackHour}
          maxHour={maxHour}
          onSeek={setPlaybackHour}
        />
        <PlaybackLineCard
          title="Resource Utilization"
          data={chartData}
          keys={[
            { key: "sts_utilization", color: "#7c3aed", label: "STS" },
            { key: "gate_utilization", color: "#0ea5e9", label: "Gate" },
            { key: "yard_utilization", color: "#16a34a", label: "Yard" },
            { key: "rail_utilization", color: "#14b8a6", label: "Rail" },
          ]}
          cursorHour={playbackHour}
          maxHour={maxHour}
          onSeek={setPlaybackHour}
        />
      </div>
    </div>
  );
}
