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

export type RunResult = {
  summary: Record<string, number>;
  timeseries: Array<Record<string, number>>;
  vessels: Array<Record<string, string | number | null>>;
  containers: Array<Record<string, string | number | null>>;
};

