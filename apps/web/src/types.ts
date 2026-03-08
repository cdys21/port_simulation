export type TriangularConfig = {
  minimum: number;
  mode: number;
  maximum: number;
};

export type ResourceConfig = {
  berths: number;
  sts_cranes: number;
  yard_equipment: number;
  gate_lanes: number;
  rail_slots: number;
};

export type GateCalendar = {
  open_hour: number;
  close_hour: number;
};

export type RailConfig = {
  import_departures_per_day: number;
  train_capacity: number;
  train_load_minutes: number;
  export_receive_minutes: TriangularConfig;
};

export type YardPolicy = {
  putaway_minutes: number;
  prestage_minutes: number;
  base_retrieve_minutes: number;
  reshuffle_minutes: number;
  alpha_putaway: number;
  beta_retrieval: number;
  congestion_threshold: number;
};

export type YardBlockConfig = {
  id: string;
  label: string;
  capacity_teu: number;
  max_stack_height: number;
};

export type ContainerTypeConfig = {
  id: string;
  label: string;
  block_id: string;
  initial_import_units: number;
  initial_export_ready_units: number;
  import_truck_share: number;
  export_truck_share: number;
  import_release_delay_hours: TriangularConfig;
  export_arrival_lead_hours: TriangularConfig;
  gate_in_minutes: TriangularConfig;
  gate_out_minutes: TriangularConfig;
  discharge_minutes: TriangularConfig;
  load_minutes: TriangularConfig;
};

export type VesselCallConfig = {
  id: string;
  name: string;
  eta_hour: number;
  export_cutoff_hours_before_eta: number;
  prestage_hours_before_eta: number;
  load_cutoff_hours_after_eta: number;
  switch_over_minutes: number;
  import_units: Record<string, number>;
  export_units: Record<string, number>;
};

export type ScenarioConfig = {
  name: string;
  description: string;
  horizon_hours: number;
  drain_hours: number;
  random_seed: number;
  vessel_delay_hours: TriangularConfig;
  resources: ResourceConfig;
  gate_calendar: GateCalendar;
  rail: RailConfig;
  yard_policy: YardPolicy;
  yard_blocks: YardBlockConfig[];
  container_types: ContainerTypeConfig[];
  vessel_calls: VesselCallConfig[];
};

export type ScenarioRecord = {
  id: string;
  created_at: string;
  updated_at: string;
  config: ScenarioConfig;
};

export type RunRecord = {
  id: string;
  scenario_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  progress: number;
  error?: string | null;
  result?: RunResult | null;
};

export type PlaybackEvent = {
  minute: number;
  hour: number;
  kind: string;
  label: string;
  zone: string;
  severity: string;
  entity_type?: string | null;
  entity_id?: string | null;
  count?: number | null;
};

export type PlaybackBlock = {
  id: string;
  label: string;
  occupancy: number;
  capacity: number;
  fill_rate: number;
};

export type PlaybackVessel = {
  id: string;
  name: string;
  zone: string;
  status: string;
  phase: string;
  remaining_imports: number;
  remaining_exports: number;
  quay_ready_exports: number;
};

export type PlaybackSnapshot = {
  minute: number;
  hour: number;
  gate_open: boolean;
  yard: {
    total_units: number;
    import_units: number;
    export_units: number;
    fill_rate: number;
  };
  queues: {
    berth_queue: number;
    gate_queue: number;
    rail_queue: number;
    yard_queue: number;
  };
  resources: {
    berths_in_use: number;
    berths_capacity: number;
    berth_utilization: number;
    sts_utilization: number;
    gate_utilization: number;
    yard_utilization: number;
    rail_utilization: number;
  };
  flows: {
    vessel_to_yard: number;
    quay_to_vessel: number;
    gate_to_yard: number;
    yard_to_gate: number;
    rail_to_yard: number;
    yard_to_rail: number;
    yard_to_quay: number;
    yard_retrieval: number;
  };
  counters: {
    import_completed: number;
    export_loaded: number;
    export_rolled: number;
  };
  blocks: PlaybackBlock[];
  vessels: PlaybackVessel[];
};

export type PlaybackBundle = {
  snapshot_interval_minutes: number;
  duration_hours: number;
  snapshots: PlaybackSnapshot[];
  events: PlaybackEvent[];
};

export type RunResult = {
  summary: Record<string, number>;
  timeseries: Array<Record<string, number>>;
  vessels: Array<Record<string, string | number | null>>;
  containers: Array<Record<string, string | number | null>>;
  playback?: PlaybackBundle | null;
};
