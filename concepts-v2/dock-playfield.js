(function () {
  const root = document.querySelector("[data-dock-playfield]");
  if (!root) {
    return;
  }

  const SLOT_POSITIONS = [0.15, 0.38, 0.61, 0.84];
  const HISTORY_KEYS = ["berth", "cranes", "forklifts", "yard", "gates"];
  const VESSEL_PATTERNS = [
    { imports: 40, exports: 20 },
    { imports: 18, exports: 42 },
    { imports: 34, exports: 26 },
    { imports: 24, exports: 36 },
  ];
  const ARRIVAL_GAPS = [3.6, 5.1, 4.2, 5.7];

  const state = {
    concept: document.body.dataset.concept || "Dock Playfield",
    speed: 8,
    timeHours: 10.0,
    berthSlots: 4,
    cranes: 6,
    forklifts: 8,
    gates: 5,
    yardCapacity: 260,
    importYard: 0,
    exportYard: 0,
    nextVesselId: 1,
    nextTruckId: 1,
    vessels: [],
    trucks: [],
    pendingImportOut: 0,
    pendingExportIn: 0,
    importDemandCarry: 0,
    exportDemandCarry: 0,
    historyCarry: 0,
    timeToNextVessel: 2.2,
    recentImportFlow: 0,
    recentExportFlow: 0,
    lastGateDirection: "export",
    histories: {
      berth: [],
      cranes: [],
      forklifts: [],
      yard: [],
      gates: [],
    },
    metrics: {
      activeBerths: 0,
      berthQueue: 0,
      activeCranes: 0,
      craneQueue: 0,
      activeForklifts: 0,
      forkliftQueue: 0,
      activeGates: 0,
      gateQueue: 0,
      yardOverflow: 0,
      forkliftAssist: 1,
      renderedGateCount: 0,
      trucksMoving: 0,
      hotLayer: "None",
    },
  };

  const controls = {
    clock: document.getElementById("clock"),
    speedValue: document.getElementById("speed-value"),
    importValue: document.getElementById("import-value"),
    exportValue: document.getElementById("export-value"),
    berthZone: document.getElementById("berth-zone"),
    craneZone: document.getElementById("crane-zone"),
    forkliftZone: document.getElementById("forklift-zone"),
    yardZone: document.getElementById("yard-zone"),
    gateZone: document.getElementById("gate-zone"),
    berthMeta: document.getElementById("berth-meta"),
    berthQueue: document.getElementById("berth-queue"),
    craneQueue: document.getElementById("crane-queue"),
    forkliftQueue: document.getElementById("forklift-queue"),
    yardQueue: document.getElementById("yard-queue"),
    gateQueue: document.getElementById("gate-queue"),
    berthHistory: document.getElementById("berth-history"),
    craneHistory: document.getElementById("crane-history"),
    forkliftHistory: document.getElementById("forklift-history"),
    yardHistory: document.getElementById("yard-history"),
    gateHistory: document.getElementById("gate-history"),
    berthSlots: document.getElementById("berth-slots"),
    vesselTrack: document.getElementById("vessel-track"),
    craneCells: document.getElementById("crane-cells"),
    forkliftCells: document.getElementById("forklift-cells"),
    gatesValue: document.getElementById("gates-value"),
    gateLanes: document.getElementById("gate-lanes"),
    truckRoad: document.getElementById("truck-road"),
    yardDots: document.getElementById("yard-dots"),
    yardCount: document.getElementById("yard-count"),
    craneValue: document.getElementById("cranes-value"),
    forkliftValue: document.getElementById("forklifts-value"),
    vesselsValue: document.getElementById("vessels-value"),
    trucksValue: document.getElementById("trucks-value"),
    yardValue: document.getElementById("yard-value"),
    pressureValue: document.getElementById("pressure-value"),
    importStream: document.getElementById("import-stream"),
    exportStream: document.getElementById("export-stream"),
  };

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function formatClock(hourValue) {
    const totalMinutes = Math.floor(hourValue * 60);
    const day = Math.floor(totalMinutes / (24 * 60));
    const dayMinutes = totalMinutes % (24 * 60);
    const hh = String(Math.floor(dayMinutes / 60)).padStart(2, "0");
    const mm = String(dayMinutes % 60).padStart(2, "0");
    return `D${day} ${hh}:${mm}`;
  }

  function queueLabel(prefix, value) {
    return `${prefix} ${Math.max(0, Math.round(value))}`;
  }

  function nextArrivalGap() {
    return ARRIVAL_GAPS[(state.nextVesselId - 1) % ARRIVAL_GAPS.length];
  }

  function createVessel(initialMode) {
    const pattern = VESSEL_PATTERNS[(state.nextVesselId - 1) % VESSEL_PATTERNS.length];
    const vessel = {
      id: `V${state.nextVesselId++}`,
      hiddenLoad: 60,
      importsRemaining: pattern.imports,
      exportsRemaining: pattern.exports,
      phase: "approach",
      workMode: initialMode || (pattern.imports >= pattern.exports ? "import" : "export"),
      slotIndex: null,
      position: -0.24,
      waitingAnchor: 0.03,
      assignedCranes: 0,
      createdAt: state.timeHours,
    };
    return vessel;
  }

  function addVessel() {
    state.vessels.push(createVessel("import"));
  }

  function removeVessel() {
    if (!state.vessels.length) {
      return;
    }
    const vessel = state.vessels[state.vessels.length - 1];
    if (vessel.phase === "berthed") {
      vessel.importsRemaining = 0;
      vessel.exportsRemaining = 0;
      vessel.phase = "departing";
      return;
    }
    state.vessels.pop();
  }

  function resetState() {
    state.timeHours = 0;
    state.importYard = 0;
    state.exportYard = 0;
    state.vessels = [];
    state.trucks = [];
    state.pendingImportOut = 0;
    state.pendingExportIn = 0;
    state.importDemandCarry = 0;
    state.exportDemandCarry = 0;
    state.historyCarry = 0;
    state.recentImportFlow = 0;
    state.recentExportFlow = 0;
    state.timeToNextVessel = 2.2;
    state.lastGateDirection = "export";
    state.histories = {
      berth: [],
      cranes: [],
      forklifts: [],
      yard: [],
      gates: [],
    };
    state.metrics = {
      activeBerths: 0,
      berthQueue: 0,
      activeCranes: 0,
      craneQueue: 0,
      activeForklifts: 0,
      forkliftQueue: 0,
      activeGates: 0,
      gateQueue: 0,
      yardOverflow: 0,
      forkliftAssist: 1,
      renderedGateCount: 0,
      trucksMoving: 0,
      hotLayer: "None",
    };
    seedHistory();
  }

  function seedState() {
    state.importYard = 84;
    state.exportYard = 56;
    const first = createVessel("import");
    first.phase = "berthed";
    first.slotIndex = 0;
    first.position = SLOT_POSITIONS[0];
    first.importsRemaining = 32;
    first.exportsRemaining = 20;

    const second = createVessel("export");
    second.phase = "berthed";
    second.slotIndex = 1;
    second.position = SLOT_POSITIONS[1];
    second.importsRemaining = 0;
    second.exportsRemaining = 28;

    state.vessels = [first, second];
    seedHistory();
  }

  function seedHistory() {
    for (const key of HISTORY_KEYS) {
      state.histories[key] = Array.from({ length: 12 }, () => 0.05);
    }
  }

  function reservedBerthSlots() {
    return new Set(
      state.vessels
        .filter((vessel) => vessel.slotIndex !== null && (vessel.phase === "approach" || vessel.phase === "berthed" || (vessel.phase === "departing" && vessel.position < 1.02)))
        .map((vessel) => vessel.slotIndex)
    );
  }

  function assignBerths() {
    const reserved = reservedBerthSlots();
    const openSlots = [];
    for (let index = 0; index < state.berthSlots; index += 1) {
      if (!reserved.has(index)) {
        openSlots.push(index);
      }
    }

    const waiting = state.vessels
      .filter((vessel) => vessel.slotIndex === null)
      .sort((left, right) => left.createdAt - right.createdAt);

    waiting.forEach((vessel, index) => {
      vessel.waitingAnchor = 0.045 + index * 0.05;
      if (openSlots.length) {
        vessel.slotIndex = openSlots.shift();
        vessel.phase = "approach";
      } else {
        vessel.phase = "waiting";
      }
    });
  }

  function allocateCranes() {
    const berthed = state.vessels.filter((vessel) => vessel.phase === "berthed");
    berthed.forEach((vessel) => {
      vessel.assignedCranes = 0;
    });

    let available = state.cranes;
    berthed.forEach((vessel) => {
      if (available > 0) {
        vessel.assignedCranes += 1;
        available -= 1;
      }
    });

    berthed
      .slice()
      .sort((left, right) => (right.importsRemaining + right.exportsRemaining) - (left.importsRemaining + left.exportsRemaining))
      .forEach((vessel) => {
        if (available > 0 && vessel.assignedCranes < 2) {
          vessel.assignedCranes += 1;
          available -= 1;
        }
      });

    state.metrics.activeCranes = berthed.reduce((sum, vessel) => sum + vessel.assignedCranes, 0);
    state.metrics.craneQueue = Math.max(0, berthed.length * 2 - state.cranes);
  }

  function updateForkliftDemand() {
    const activeGateOrQueue = state.trucks.filter((truck) => truck.phase === "service" || truck.phase === "approach").length + state.pendingImportOut + state.pendingExportIn;
    const demand = Math.ceil(state.metrics.activeCranes * 0.9 + activeGateOrQueue * 0.45);
    state.metrics.activeForklifts = Math.min(state.forklifts, demand);
    state.metrics.forkliftQueue = Math.max(0, demand - state.forklifts);
    state.metrics.forkliftAssist = demand === 0 ? 1 : clamp(state.metrics.activeForklifts / demand, 0.48, 1);
  }

  function updateVessels(seconds, simHours) {
    assignBerths();
    allocateCranes();
    updateForkliftDemand();

    let importMoved = 0;
    let exportMoved = 0;

    state.vessels.forEach((vessel) => {
      if (vessel.phase === "approach") {
        const target = vessel.slotIndex === null ? vessel.waitingAnchor : SLOT_POSITIONS[vessel.slotIndex];
        const pull = Math.min(1, seconds * (2.8 + state.speed * 0.1));
        vessel.position += (target - vessel.position) * pull;
        if (vessel.slotIndex !== null && Math.abs(vessel.position - target) < 0.012) {
          vessel.position = target;
          vessel.phase = "berthed";
        }
        return;
      }

      if (vessel.phase === "waiting") {
        const pull = Math.min(1, seconds * 5);
        vessel.position += (vessel.waitingAnchor - vessel.position) * pull;
        return;
      }

      if (vessel.phase === "berthed") {
        const rate = vessel.assignedCranes * 3.4 * state.metrics.forkliftAssist;
        if (vessel.importsRemaining > 0.2) {
          const moved = Math.min(vessel.importsRemaining, rate * simHours);
          vessel.importsRemaining -= moved;
          importMoved += moved;
          state.importYard += moved;
          vessel.workMode = "import";
          return;
        }

        if (vessel.exportsRemaining > 0.2) {
          const moved = Math.min(vessel.exportsRemaining, state.exportYard, rate * 0.92 * simHours);
          vessel.exportsRemaining -= moved;
          state.exportYard = Math.max(0, state.exportYard - moved);
          exportMoved += moved;
          vessel.workMode = "export";
          return;
        }

        vessel.phase = "departing";
        vessel.workMode = "departing";
        return;
      }

      if (vessel.phase === "departing") {
        vessel.position += seconds * (0.95 + state.speed * 0.045);
      }
    });

    state.vessels = state.vessels.filter((vessel) => vessel.position < 1.18);
    state.recentImportFlow = state.recentImportFlow * 0.7 + importMoved * 0.8;
    state.recentExportFlow = state.recentExportFlow * 0.7 + exportMoved * 0.85;
  }

  function scheduleTruckDemand(simHours) {
    const exportRate = 1.0 + state.vessels.filter((vessel) => vessel.phase === "berthed").length * 0.18;
    const importRate = Math.min(state.importYard / 36, 1.8);
    state.exportDemandCarry += exportRate * simHours;
    state.importDemandCarry += importRate * simHours;

    while (state.exportDemandCarry >= 1) {
      state.pendingExportIn += 1;
      state.exportDemandCarry -= 1;
    }

    while (state.importDemandCarry >= 1) {
      state.pendingImportOut += 1;
      state.importDemandCarry -= 1;
    }
  }

  function reserveGateCount() {
    return state.trucks.filter((truck) => truck.phase === "approach" || truck.phase === "service").length;
  }

  function nextOpenLane() {
    const reserved = new Set(
      state.trucks
        .filter((truck) => truck.phase === "approach" || truck.phase === "service")
        .map((truck) => truck.laneIndex)
    );
    const renderCount = Math.max(state.gates, ...Array.from(reserved.values(), (value) => value + 1), 1);
    for (let index = 0; index < renderCount; index += 1) {
      if (!reserved.has(index)) {
        return index;
      }
    }
    return renderCount;
  }

  function assignTrucksToGates() {
    while (reserveGateCount() < state.gates && (state.pendingExportIn > 0 || state.pendingImportOut > 0)) {
      const preferImport = state.pendingImportOut > 0 && (state.lastGateDirection === "export" || state.pendingImportOut > state.pendingExportIn);
      const kind = preferImport ? "import" : "export";
      if (kind === "import" && state.importYard <= 0) {
        if (state.pendingExportIn > 0) {
          state.lastGateDirection = "import";
        } else {
          break;
        }
      }

      const laneIndex = nextOpenLane();
      const truck = {
        id: `T${state.nextTruckId++}`,
        kind,
        phase: "approach",
        laneIndex,
        y: kind === "export" ? 96 : 14,
        serviceRemaining: 0.46,
      };

      if (kind === "import") {
        state.pendingImportOut = Math.max(0, state.pendingImportOut - 1);
        state.importYard = Math.max(0, state.importYard - 4);
      } else {
        state.pendingExportIn = Math.max(0, state.pendingExportIn - 1);
      }

      state.lastGateDirection = kind;
      state.trucks.push(truck);
    }
  }

  function updateTrucks(seconds, simHours) {
    assignTrucksToGates();

    state.trucks.forEach((truck) => {
      const motion = seconds * (38 + state.speed * 2.4);
      if (truck.phase === "approach") {
        if (truck.kind === "export") {
          truck.y -= motion;
          if (truck.y <= 52) {
            truck.y = 52;
            truck.phase = "service";
          }
        } else {
          truck.y += motion;
          if (truck.y >= 52) {
            truck.y = 52;
            truck.phase = "service";
          }
        }
        return;
      }

      if (truck.phase === "service") {
        truck.serviceRemaining -= simHours;
        if (truck.serviceRemaining <= 0) {
          if (truck.kind === "export") {
            state.exportYard += 4;
            truck.phase = "handoff";
          } else {
            truck.phase = "depart";
          }
        }
        return;
      }

      if (truck.phase === "handoff") {
        truck.y -= motion;
        return;
      }

      if (truck.phase === "depart") {
        truck.y += motion;
      }
    });

    state.trucks = state.trucks.filter((truck) => truck.y > -8 && truck.y < 108);
    state.metrics.activeGates = state.trucks.filter((truck) => truck.phase === "service").length;
    state.metrics.gateQueue = state.pendingExportIn + state.pendingImportOut + Math.max(0, reserveGateCount() - state.gates);
    state.metrics.trucksMoving = state.trucks.filter((truck) => truck.phase !== "service").length;
    state.metrics.renderedGateCount = Math.max(state.gates, ...state.trucks.map((truck) => truck.laneIndex + 1), 1);
  }

  function autoInjectVessels(simHours) {
    state.timeToNextVessel -= simHours;
    if (state.timeToNextVessel <= 0) {
      addVessel();
      state.timeToNextVessel = nextArrivalGap();
    }
  }

  function updateMetrics() {
    const occupied = new Set(
      state.vessels
        .filter((vessel) => vessel.slotIndex !== null && (vessel.phase === "approach" || vessel.phase === "berthed" || (vessel.phase === "departing" && vessel.position < 1.02)))
        .map((vessel) => vessel.slotIndex)
    );
    state.metrics.activeBerths = occupied.size;
    state.metrics.berthQueue = state.vessels.filter((vessel) => vessel.slotIndex === null).length;
    state.metrics.yardOverflow = Math.max(0, state.importYard + state.exportYard - state.yardCapacity);

    const layerScores = [
      { name: "Berths", score: state.berthSlots ? state.metrics.activeBerths / state.berthSlots + state.metrics.berthQueue * 0.4 : 0 },
      { name: "Cranes", score: state.cranes ? state.metrics.activeCranes / state.cranes + state.metrics.craneQueue * 0.35 : 0 },
      { name: "Forklifts", score: state.forklifts ? state.metrics.activeForklifts / state.forklifts + state.metrics.forkliftQueue * 0.25 : 0 },
      { name: "Yard", score: state.yardCapacity ? (state.importYard + state.exportYard) / state.yardCapacity : 0 },
      { name: "Gates", score: state.gates ? state.metrics.activeGates / state.gates + state.metrics.gateQueue * 0.25 : 0 },
    ];

    const topLayer = layerScores.sort((left, right) => right.score - left.score)[0];
    state.metrics.hotLayer = topLayer && topLayer.score > 0.02 ? topLayer.name : "None";
  }

  function refreshDerivedState() {
    assignBerths();
    allocateCranes();
    updateForkliftDemand();
    updateMetrics();
  }

  function recordHistory(simHours, force) {
    state.historyCarry += simHours;
    if (!force && state.historyCarry < 0.25) {
      return;
    }
    if (!force) {
      state.historyCarry = 0;
    }

    const samples = {
      berth: state.berthSlots ? state.metrics.activeBerths / state.berthSlots : 0,
      cranes: state.cranes ? state.metrics.activeCranes / state.cranes : 0,
      forklifts: state.forklifts ? state.metrics.activeForklifts / state.forklifts : 0,
      yard: state.yardCapacity ? (state.importYard + state.exportYard) / state.yardCapacity : 0,
      gates: state.gates ? state.metrics.activeGates / state.gates : 0,
    };

    HISTORY_KEYS.forEach((key) => {
      state.histories[key].push(samples[key]);
      if (state.histories[key].length > 12) {
        state.histories[key].shift();
      }
    });
  }

  function zoneStateFrom(utilization, queueValue) {
    if (queueValue > 0 || utilization > 1) {
      return "over";
    }
    if (utilization > 0.78) {
      return "high";
    }
    if (utilization > 0.4) {
      return "med";
    }
    return "low";
  }

  function setZoneClass(target, utilization, queueValue) {
    if (!target) {
      return;
    }
    target.classList.remove("util-low", "util-med", "util-high", "util-over");
    target.classList.add(`util-${zoneStateFrom(utilization, queueValue)}`);
  }

  function renderQueue(target, prefix, value) {
    if (!target) {
      return;
    }
    target.textContent = queueLabel(prefix, value);
    target.classList.toggle("active", value > 0);
  }

  function renderHistory(target, points) {
    if (!target) {
      return;
    }
    target.innerHTML = "";
    points.forEach((point) => {
      const bar = document.createElement("span");
      const bounded = clamp(point, 0.08, 1.14);
      bar.className = `history-bar ${bounded > 0.78 ? "hot" : ""}`.trim();
      bar.style.height = `${Math.round(bounded * 38)}px`;
      target.appendChild(bar);
    });
  }

  function renderBerthSlots() {
    if (!controls.berthSlots) {
      return;
    }
    controls.berthSlots.innerHTML = "";
    for (let index = 0; index < state.berthSlots; index += 1) {
      const slot = document.createElement("div");
      const vessel = state.vessels.find(
        (candidate) =>
          candidate.slotIndex === index &&
          (candidate.phase === "approach" || candidate.phase === "berthed" || (candidate.phase === "departing" && candidate.position < 1.02))
      );
      const mode = vessel?.workMode === "export" ? "export" : "import";
      slot.className = `berth-slot ${vessel ? `occupied ${mode}` : ""}`.trim();
      slot.innerHTML = vessel
        ? `<strong>Berth ${index + 1}</strong><span>${vessel.id} ${vessel.phase === "berthed" ? `${mode} work` : vessel.phase}</span>`
        : `<strong>Berth ${index + 1}</strong><span>open slot</span>`;
      controls.berthSlots.appendChild(slot);
    }
  }

  function renderVessels() {
    if (!controls.vesselTrack) {
      return;
    }
    controls.vesselTrack.innerHTML = "";
    let waitingRow = 0;

    state.vessels.forEach((vessel) => {
      const node = document.createElement("div");
      const mode = vessel.workMode === "export" ? "export" : "import";
      const phaseClass = vessel.phase === "waiting" ? "waiting" : vessel.phase;
      node.className = `vessel ${phaseClass} ${mode}`.trim();
      node.style.left = `${clamp(8 + vessel.position * 82, -8, 108)}%`;
      if (vessel.phase === "waiting") {
        node.style.top = `${24 + waitingRow * 20}px`;
        waitingRow += 1;
      } else {
        node.style.top = "50%";
      }
      const label =
        vessel.phase === "berthed"
          ? `${vessel.assignedCranes} cranes`
          : vessel.phase === "departing"
            ? "leaving fast"
            : vessel.phase === "approach"
              ? "arriving fast"
              : "berth queue";
      node.innerHTML = `<strong>${vessel.id}</strong><span>${label}</span>`;
      controls.vesselTrack.appendChild(node);
    });
  }

  function renderResourceCells(target, total, active, label) {
    if (!target) {
      return;
    }
    target.innerHTML = "";
    for (let index = 0; index < total; index += 1) {
      const cell = document.createElement("div");
      const isActive = index < active;
      cell.className = `resource-cell ${isActive ? "active" : "idle"} ${index + 1 === total && active === total && total > 0 ? "saturated" : ""}`.trim();
      cell.textContent = label;
      target.appendChild(cell);
    }
  }

  function renderYardDots() {
    if (!controls.yardDots) {
      return;
    }
    controls.yardDots.innerHTML = "";

    const importDots = clamp(Math.round(state.importYard / 4), 0, 42);
    const exportDots = clamp(Math.round(state.exportYard / 4), 0, 28);
    const overflowDots = clamp(Math.round(state.metrics.yardOverflow / 3), 0, 18);

    for (let index = 0; index < importDots; index += 1) {
      const dot = document.createElement("span");
      dot.className = "yard-dot";
      controls.yardDots.appendChild(dot);
    }

    for (let index = 0; index < exportDots; index += 1) {
      const dot = document.createElement("span");
      dot.className = "yard-dot export";
      controls.yardDots.appendChild(dot);
    }

    for (let index = 0; index < overflowDots; index += 1) {
      const dot = document.createElement("span");
      dot.className = "yard-dot overflow";
      controls.yardDots.appendChild(dot);
    }
  }

  function gateLaneCenters(count) {
    return Array.from({ length: count }, (_, index) => ((index + 0.5) / count) * 100);
  }

  function renderGateLanes() {
    if (!controls.gateLanes) {
      return;
    }
    const count = Math.max(state.gates, state.metrics.renderedGateCount, 1);
    const serviceByLane = new Map(
      state.trucks.filter((truck) => truck.phase === "service").map((truck) => [truck.laneIndex, truck])
    );
    controls.gateLanes.innerHTML = "";

    for (let index = 0; index < count; index += 1) {
      const lane = document.createElement("div");
      const truck = serviceByLane.get(index);
      const direction = truck?.kind || "idle";
      lane.className = `gate-lane ${truck ? `active ${direction}` : ""}`.trim();
      const label = index < state.gates ? `Gate ${index + 1}` : `Hold ${index + 1}`;
      const detail = truck ? (truck.kind === "export" ? "truck in" : "truck out") : index < state.gates ? "ready" : "draining";
      lane.innerHTML = `<strong>${label}</strong><span>${detail}</span>`;
      controls.gateLanes.appendChild(lane);
    }
  }

  function renderTrucks() {
    if (!controls.truckRoad) {
      return;
    }
    controls.truckRoad.innerHTML = "";
    const count = Math.max(state.gates, state.metrics.renderedGateCount, 1);
    const centers = gateLaneCenters(count);

    state.trucks.forEach((truck) => {
      const node = document.createElement("div");
      node.className = `truck ${truck.kind} ${truck.phase === "service" ? "service" : ""}`.trim();
      node.textContent = truck.kind === "export" ? "IN" : "OUT";
      node.style.left = `${centers[truck.laneIndex] || centers[centers.length - 1]}%`;
      node.style.top = `${clamp(truck.y, 4, 96)}%`;
      controls.truckRoad.appendChild(node);
    });
  }

  function renderFlowDots(target, count, className) {
    if (!target) {
      return;
    }
    target.innerHTML = "";
    const columns = className === "import" ? [18, 30, 42, 54, 66] : [26, 38, 50, 62, 74];
    for (let index = 0; index < count; index += 1) {
      const dot = document.createElement("span");
      dot.className = `flow-dot ${className}`;
      dot.style.left = `${columns[index % columns.length]}%`;
      dot.style.animationDelay = `${(index % 10) * -0.18}s`;
      target.appendChild(dot);
    }
  }

  function render() {
    const berthUtil = state.berthSlots ? state.metrics.activeBerths / state.berthSlots : 0;
    const craneUtil = state.cranes ? state.metrics.activeCranes / state.cranes : 0;
    const forkliftUtil = state.forklifts ? state.metrics.activeForklifts / state.forklifts : 0;
    const yardUtil = state.yardCapacity ? (state.importYard + state.exportYard) / state.yardCapacity : 0;
    const gateUtil = state.gates ? state.metrics.activeGates / state.gates : 0;

    setZoneClass(controls.berthZone, berthUtil, state.metrics.berthQueue);
    setZoneClass(controls.craneZone, craneUtil, state.metrics.craneQueue);
    setZoneClass(controls.forkliftZone, forkliftUtil, state.metrics.forkliftQueue);
    setZoneClass(controls.yardZone, yardUtil, state.metrics.yardOverflow);
    setZoneClass(controls.gateZone, gateUtil, state.metrics.gateQueue);

    renderQueue(controls.berthQueue, "Queue", state.metrics.berthQueue);
    renderQueue(controls.craneQueue, "Queue", state.metrics.craneQueue);
    renderQueue(controls.forkliftQueue, "Queue", state.metrics.forkliftQueue);
    renderQueue(controls.yardQueue, "Overflow", state.metrics.yardOverflow);
    renderQueue(controls.gateQueue, "Queue", state.metrics.gateQueue);

    renderHistory(controls.berthHistory, state.histories.berth);
    renderHistory(controls.craneHistory, state.histories.cranes);
    renderHistory(controls.forkliftHistory, state.histories.forklifts);
    renderHistory(controls.yardHistory, state.histories.yard);
    renderHistory(controls.gateHistory, state.histories.gates);

    renderBerthSlots();
    renderVessels();
    renderResourceCells(controls.craneCells, state.cranes, state.metrics.activeCranes, "C");
    renderResourceCells(controls.forkliftCells, state.forklifts, state.metrics.activeForklifts, "F");
    renderYardDots();
    renderGateLanes();
    renderTrucks();

    const importDots = clamp(Math.round(state.recentImportFlow), 0, 18);
    const exportDots = clamp(Math.round(state.recentExportFlow), 0, 18);
    renderFlowDots(controls.importStream, importDots, "import");
    renderFlowDots(controls.exportStream, exportDots, "export");

    if (controls.clock) controls.clock.textContent = formatClock(state.timeHours);
    if (controls.speedValue) controls.speedValue.textContent = `${state.speed}x`;
    if (controls.importValue) controls.importValue.textContent = `${importDots} down`;
    if (controls.exportValue) controls.exportValue.textContent = `${exportDots} up`;
    if (controls.berthMeta) controls.berthMeta.textContent = `${state.metrics.activeBerths}/${state.berthSlots} occupied, arrivals left and departures right`;
    if (controls.craneValue) controls.craneValue.textContent = `${state.metrics.activeCranes}/${state.cranes} active`;
    if (controls.forkliftValue) controls.forkliftValue.textContent = `${state.metrics.activeForklifts}/${state.forklifts} active`;
    if (controls.gatesValue) controls.gatesValue.textContent = `${state.metrics.activeGates}/${state.gates} active`;
    if (controls.vesselsValue) controls.vesselsValue.textContent = String(state.vessels.length);
    if (controls.trucksValue) controls.trucksValue.textContent = String(state.metrics.trucksMoving);
    if (controls.yardCount) controls.yardCount.textContent = `${Math.round(state.importYard + state.exportYard)} of ${state.yardCapacity}`;
    if (controls.yardValue) controls.yardValue.textContent = `${Math.round(state.importYard + state.exportYard)} / ${state.yardCapacity}`;
    if (controls.pressureValue) controls.pressureValue.textContent = state.metrics.hotLayer;
  }

  function stepSimulation(seconds) {
    const simHours = (seconds * state.speed) / 6;
    state.timeHours += simHours;
    autoInjectVessels(simHours);
    scheduleTruckDemand(simHours);
    updateVessels(seconds, simHours);
    updateTrucks(seconds, simHours);
    updateMetrics();
    recordHistory(simHours, false);
  }

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.getAttribute("data-action");
      if (action === "add-vessel") addVessel();
      if (action === "remove-vessel") removeVessel();
      if (action === "inc-cranes") state.cranes += 1;
      if (action === "dec-cranes") state.cranes = Math.max(0, state.cranes - 1);
      if (action === "inc-forklifts") state.forklifts += 1;
      if (action === "dec-forklifts") state.forklifts = Math.max(0, state.forklifts - 1);
      if (action === "inc-gates") state.gates += 1;
      if (action === "dec-gates") state.gates = Math.max(0, state.gates - 1);
      if (action === "reset") resetState();
      refreshDerivedState();
      recordHistory(0.25, true);
      render();
    });
  });

  document.querySelectorAll("[data-speed]").forEach((button) => {
    button.addEventListener("click", () => {
      state.speed = Number(button.getAttribute("data-speed")) || state.speed;
      document.querySelectorAll("[data-speed]").forEach((node) => node.classList.remove("selected"));
      button.classList.add("selected");
      render();
    });
  });

  window.render_game_to_text = function renderGameToText() {
    return JSON.stringify({
      concept: state.concept,
      coordinate_system: "Berths at top. Imports flow downward. Exports flow upward. Vessels arrive from left, berth, then depart right. Trucks move through gates and stop while in service.",
      clock: formatClock(state.timeHours),
      vessels: state.vessels.map((vessel) => ({
        id: vessel.id,
        phase: vessel.phase,
        slot: vessel.slotIndex,
        mode: vessel.workMode,
      })),
      trucks: {
        moving: state.metrics.trucksMoving,
        service: state.metrics.activeGates,
        waiting: state.metrics.gateQueue,
      },
      layers: {
        berths: { active: state.metrics.activeBerths, total: state.berthSlots, queue: state.metrics.berthQueue },
        cranes: { active: state.metrics.activeCranes, total: state.cranes, queue: state.metrics.craneQueue },
        forklifts: { active: state.metrics.activeForklifts, total: state.forklifts, queue: state.metrics.forkliftQueue },
        yard: { load: Math.round(state.importYard + state.exportYard), capacity: state.yardCapacity, overflow: Math.round(state.metrics.yardOverflow) },
        gates: { active: state.metrics.activeGates, total: state.gates, queue: state.metrics.gateQueue },
      },
      flows: {
        imports_down: clamp(Math.round(state.recentImportFlow), 0, 18),
        exports_up: clamp(Math.round(state.recentExportFlow), 0, 18),
      },
      hot_layer: state.metrics.hotLayer,
    });
  };

  window.advanceTime = function advanceTime(ms) {
    stepSimulation(ms / 1000);
    render();
  };

  seedState();
  refreshDerivedState();
  recordHistory(0.25, true);
  render();

  setInterval(() => {
    stepSimulation(0.12);
    render();
  }, 120);
})();
