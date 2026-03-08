(function () {
  const root = document.querySelector("[data-live-ops]");
  if (!root) {
    return;
  }

  const state = {
    concept: document.body.dataset.concept || "Live Ops",
    berthSlots: 4,
    speed: 8,
    timeHours: 12.4,
    nextVesselId: 1,
    vessels: [],
    cranes: 6,
    activeCranes: 0,
    forklifts: 8,
    activeForklifts: 0,
    gates: 5,
    activeGates: 0,
    yardCapacity: 260,
    yardCount: 92,
    importDots: 0,
    exportDots: 0,
    live: true,
  };

  const controls = {
    clock: document.getElementById("clock"),
    vesselTrack: document.getElementById("vessel-track"),
    berthSlots: document.getElementById("berth-slots"),
    craneCells: document.getElementById("crane-cells"),
    forkliftCells: document.getElementById("forklift-cells"),
    gateCells: document.getElementById("gate-cells"),
    yardCount: document.getElementById("yard-count"),
    yardDots: document.getElementById("yard-dots"),
    importStream: document.getElementById("import-stream"),
    exportStream: document.getElementById("export-stream"),
    vesselsValue: document.getElementById("vessels-value"),
    cranesValue: document.getElementById("cranes-value"),
    forkliftsValue: document.getElementById("forklifts-value"),
    gatesValue: document.getElementById("gates-value"),
    speedValue: document.getElementById("speed-value"),
    yardValue: document.getElementById("yard-value"),
    importValue: document.getElementById("import-value"),
    exportValue: document.getElementById("export-value"),
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

  function createVessel(progress) {
    return {
      id: `V${state.nextVesselId++}`,
      progress,
    };
  }

  function seedState() {
    state.vessels = [createVessel(0.08), createVessel(0.28)];
    state.yardCount = 92;
    recalculate();
  }

  function resetState() {
    state.timeHours = 0;
    state.vessels = [];
    state.yardCount = 0;
    state.importDots = 0;
    state.exportDots = 0;
    recalculate();
  }

  function addVessel() {
    state.vessels.push(createVessel(-0.18));
    recalculate();
    render();
  }

  function removeVessel() {
    state.vessels.pop();
    recalculate();
    render();
  }

  function recalculate() {
    const workingVessels = state.vessels.filter((vessel) => vessel.progress > 0.08 && vessel.progress < 0.82).length;
    state.activeCranes = Math.min(state.cranes, workingVessels * 2);
    const importRate = workingVessels * Math.max(1, state.activeCranes) * 0.9;
    const exportRate = Math.min(state.yardCount / 16, workingVessels > 0 ? workingVessels * 2.8 : 0);
    state.activeForklifts = Math.min(state.forklifts, Math.ceil((importRate + exportRate) / 4));
    state.activeGates = Math.min(state.gates, Math.ceil(exportRate / 2));
    state.importDots = clamp(Math.round(importRate), 0, 24);
    state.exportDots = clamp(Math.round(exportRate + state.activeGates * 0.6), 0, 24);
  }

  function stepSimulation(seconds) {
    state.timeHours += (seconds * state.speed) / 6;

    for (const vessel of state.vessels) {
      vessel.progress += seconds * 0.028 * (0.8 + state.speed / 10);
    }

    state.vessels = state.vessels.filter((vessel) => vessel.progress < 1.16);

    recalculate();

    const importPressure = state.importDots * 0.18;
    const exportRelief = state.exportDots * 0.12 + state.activeGates * 0.08;
    state.yardCount = clamp(state.yardCount + importPressure - exportRelief, 0, state.yardCapacity);
    recalculate();
  }

  function renderCells(target, total, active, label) {
    if (!target) {
      return;
    }
    target.innerHTML = "";
    for (let index = 0; index < total; index += 1) {
      const cell = document.createElement("div");
      cell.className = `resource-cell ${index < active ? "active" : "idle"}`;
      cell.textContent = label;
      target.appendChild(cell);
    }
  }

  function renderBerthSlots() {
    if (!controls.berthSlots || controls.berthSlots.childElementCount) {
      return;
    }
    for (let index = 0; index < state.berthSlots; index += 1) {
      const slot = document.createElement("div");
      slot.className = "berth-slot";
      slot.innerHTML = `<strong>Berth ${index + 1}</strong><span>arrival left -> depart right</span>`;
      controls.berthSlots.appendChild(slot);
    }
  }

  function renderVessels() {
    if (!controls.vesselTrack) {
      return;
    }
    controls.vesselTrack.innerHTML = "";
    state.vessels.forEach((vessel, index) => {
      const node = document.createElement("div");
      node.className = "vessel";
      node.style.left = `${6 + vessel.progress * 78}%`;
      node.style.top = `${14 + (index % 2) * 26}px`;
      node.innerHTML = `<strong>${vessel.id}</strong><span>hidden load</span>`;
      controls.vesselTrack.appendChild(node);
    });
  }

  function renderDots(target, count, className) {
    if (!target) {
      return;
    }
    target.innerHTML = "";
    const columns = [20, 37, 54, 71];
    for (let index = 0; index < count; index += 1) {
      const dot = document.createElement("span");
      dot.className = `flow-dot ${className}`;
      dot.style.left = `${columns[index % columns.length]}%`;
      dot.style.animationDelay = `${(index % 8) * -0.28}s`;
      target.appendChild(dot);
    }
  }

  function renderYardDots() {
    if (!controls.yardDots) {
      return;
    }
    controls.yardDots.innerHTML = "";
    const count = clamp(Math.round(state.yardCount / 3), 0, 90);
    for (let index = 0; index < count; index += 1) {
      const dot = document.createElement("span");
      dot.className = "yard-dot";
      controls.yardDots.appendChild(dot);
    }
  }

  function render() {
    renderBerthSlots();
    renderVessels();
    renderCells(controls.craneCells, state.cranes, state.activeCranes, "C");
    renderCells(controls.forkliftCells, state.forklifts, state.activeForklifts, "F");
    renderCells(controls.gateCells, state.gates, state.activeGates, "G");
    renderDots(controls.importStream, state.importDots, "import");
    renderDots(controls.exportStream, state.exportDots, "export");
    renderYardDots();

    if (controls.clock) controls.clock.textContent = formatClock(state.timeHours);
    if (controls.vesselsValue) controls.vesselsValue.textContent = String(state.vessels.length);
    if (controls.cranesValue) controls.cranesValue.textContent = `${state.activeCranes}/${state.cranes}`;
    if (controls.forkliftsValue) controls.forkliftsValue.textContent = `${state.activeForklifts}/${state.forklifts}`;
    if (controls.gatesValue) controls.gatesValue.textContent = `${state.activeGates}/${state.gates}`;
    if (controls.speedValue) controls.speedValue.textContent = `${state.speed}x`;
    if (controls.yardValue) controls.yardValue.textContent = `${Math.round(state.yardCount)} / ${state.yardCapacity}`;
    if (controls.yardCount) controls.yardCount.textContent = `${Math.round(state.yardCount)} of ${state.yardCapacity}`;
    if (controls.importValue) controls.importValue.textContent = `${state.importDots} active lanes down`;
    if (controls.exportValue) controls.exportValue.textContent = `${state.exportDots} active lanes up`;
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
      recalculate();
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
      coordinate_system: "Berths at top. Imports flow downward. Exports flow upward. Vessels move left to right.",
      clock: formatClock(state.timeHours),
      vessels: state.vessels.map((vessel) => ({ id: vessel.id, progress: Number(vessel.progress.toFixed(2)) })),
      cranes: { total: state.cranes, active: state.activeCranes },
      forklifts: { total: state.forklifts, active: state.activeForklifts },
      gates: { total: state.gates, active: state.activeGates },
      yard: { count: Math.round(state.yardCount), capacity: state.yardCapacity },
      flows: { imports_down: state.importDots, exports_up: state.exportDots },
    });
  };

  window.advanceTime = function advanceTime(ms) {
    stepSimulation(ms / 1000);
    render();
  };

  seedState();
  render();

  setInterval(() => {
    stepSimulation(0.12);
    render();
  }, 120);
})();
