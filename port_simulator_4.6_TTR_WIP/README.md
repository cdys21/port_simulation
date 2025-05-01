# readme

# Container Terminal Simulation with Resilience Analysis

This release adds a **Resilience Experiment** layer on top of the base port simulation:

1. **One‑Shock‑per‑Run**  
   Inject exactly one disruption (gate outage or crane failure) at a random time within a user‑specified window.

2. **Configurable Parameters**  
   - Number of runs per shock type  
   - Disruption window & duration  
   - Recovery threshold for yard occupancy  

3. **Recovery Metrics**  
   - **Time to Recovery (TTR):** how long until total yard occupancy returns to its pre‑shock level.  
   - **Time to Zero:** how long until the yard fully empties.

4. **Batch Experiments & Reporting**  
   - Run N replicates per shock type.  
   - Streamlit UI to launch experiments.  
   - Summary table and box‑and‑whisker plots by disruption type.

---

With this setup you can directly compare port resilience across different disruption modes, durations, and parameter settings.
