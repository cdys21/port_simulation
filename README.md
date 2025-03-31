# Port Simulation README

## Overview

This project attempts to simulate the dynamic flow of import containers through a port system. The simulation is designed to help stakeholders understand the complexities of container import operations from a container’s arrival on a ship to its departure via inland transportation. In real-world settings, these processes involve many steps and parties. This code provides a starting point to identify bottlenecks, test new ideas, and evaluate their impact on the overall port system rather than focusing on isolated components. Ultimately, the simulation aims to improve collaboration and operational resilience among all parties involved.

## Process Overview

The simulation models a complete port operation workflow, including:

- **Ship Arrival:** Vessels arrive based on a predefined schedule, with actual arrival times adjusted by a variability factor.
- **Container Unloading:** Once a ship docks at an available berth, containers are unloaded by cranes. The unloading process is subject to delays and variability.
- **Yard Storage and Stacking:** Unloaded containers are moved to the yard. Their stacking level is determined based on current yard utilization, which in turn affects the time needed for retrieval.
- **Gate and Inland Transport:** Containers leave the yard via trucks or trains. The departure process includes gate processing times and, for train departures, scheduling based on capacity.
- **Resource Monitoring:** Throughout the simulation, key metrics such as equipment utilization (berths, cranes, gate, yard) and container dwell times are tracked.

## Code Structure

The project is organized into several modules, each with a distinct role:

- **config.py:**  
  Contains all default simulation parameters. This includes the ship schedule, equipment capacities, processing times, variability settings, and other adjustable parameters. It serves as the central configuration hub for the simulation.

- **main.py:**  
  Acts as the entry point. It sets up a Streamlit-based user interface for editing simulation parameters, displaying ship schedules, and running the simulation. It also calls functions that generate visualizations and statistical outputs.

- **models.py:**  
  Defines the core classes:
  - **Container:** Represents individual containers with attributes such as type, transportation mode (truck or train), and timing details.
  - **Ship:** Represents vessels arriving at the port and is responsible for generating container objects.
  - **ShipSchedule:** Manages the schedule of incoming ships, storing information in a pandas DataFrame.

- **rules.py:**  
  Implements key decision rules and computations used across the simulation. These include:
  - **determine_stacking_level:** Calculates the stacking level for new containers based on current yard utilization.
  - **calculate_stacking_retrieval_time:** Computes additional retrieval time based on stacking level and yard congestion.
  - **calculate_actual_arrival:** Adjusts the expected vessel arrival time by introducing a random variability factor.

- **simulation.py:**  
  Contains the simulation engine built using SimPy. The `PortSimulation` class orchestrates the complete process—from scheduling ships and unloading containers to processing yard movements and handling departures. It also integrates real-time progress monitoring via Streamlit.

- **statistics.py:**  
  Aggregates and computes performance metrics such as dwell times, wait times, and equipment utilization. This module is essential for analyzing simulation outcomes and generating insights into operational performance.

- **ui.py:**  
  Provides interactive visualizations using Plotly and Streamlit. It generates charts, histograms, waterfall diagrams, and animated plots to help users explore and understand the simulation results in a data-driven manner.

## Rules / Assumptions

The simulation is driven by several key rules and assumptions that capture the uncertainties and operational decisions inherent in port operations:

- **Uncertainty in Vessel Arrival:**  
  Expected vessel arrival times are adjusted by a random variability factor. The function `calculate_actual_arrival` in **rules.py** applies a normal distribution to model schedule deviations, reflecting the unpredictable nature of maritime transport.

- **Container Stacking Rule:**  
  When containers are unloaded into the yard, their stacking level is determined by the current yard utilization. The `determine_stacking_level` function (used in both **rules.py** and **simulation.py**) creates a probability distribution for stacking levels from 1 up to the maximum allowed height. This rule simulates how higher yard occupancy increases the likelihood of containers being stacked higher, directly influencing retrieval times.

- **Retrieval Time Estimation:**  
  The function `calculate_stacking_retrieval_time` (in **rules.py**) calculates the additional time needed to retrieve a container based on its stacking level and yard congestion. A congestion factor is applied when yard utilization exceeds a certain threshold, mirroring the increased complexity of operations in a crowded yard.

- **Container Departure Order:**  
  The model assumes a first-come, first-served approach for container departures:
  - **Truck Departures:** Each container is processed individually once the gate is open, with departure timing determined by the container’s readiness and associated retrieval times.
  - **Train Departures:** Containers scheduled for train transport are sorted by their waiting time (`departure_wait_start`). This ensures that containers waiting longer are prioritized, simulating realistic departure scheduling.

- **Equipment Availability & Operational Factors:**  
  Adjustable parameters in **config.py** account for the effective availability of berths, cranes, gates, and yard space. These multipliers allow the simulation to model scenarios where equipment does not operate at full capacity due to maintenance, inefficiencies, or external constraints.

## Guidelines for Updating Simulation Rules and Assumptions

To tailor the simulation to different operational scenarios or to experiment with new assumptions, please update the following files as described below:

- **rules.py:**  
  This file encapsulates the core mathematical models and decision logic behind key operational assumptions. You can update:
  - **Container Stacking Logic:**  
    Modify the `determine_stacking_level` function to change how the stacking level is computed based on current yard utilization.
  - **Retrieval Time Calculation:**  
    Adjust the `calculate_stacking_retrieval_time` function to refine how stacking level and yard congestion determine the extra time required to retrieve a container.
  - **Vessel Arrival Variability:**  
    Update the `calculate_actual_arrival` function to change how expected vessel arrival times are modified by random variability, reflecting real-world uncertainties.

- **simulation.py:**  
  This module coordinates the overall simulation workflow. You can update:
  - **Ship Scheduling & Container Processing:**  
    Alter the sequence in which ships are scheduled, containers are unloaded, and yard operations are executed. This includes the logic for triggering container processing upon arrival.
  - **Departure Sequencing:**  
    Modify the rules that determine the order in which containers depart via truck or train, including any prioritization based on waiting time.
  - **Resource Allocation and Monitoring:**  
    Adjust how the simulation allocates and tracks usage of resources such as berths, cranes, gates, and yard space.

- **config.py:**  
  This file contains all adjustable parameters that set up the simulation environment. You can update:
  - **Default Operational Parameters:**  
    Change settings such as the ship schedule, equipment capacities (e.g., number of berths, cranes per berth), processing times (e.g., container unload time, berth transition time), and variability parameters.
  - **Modal Splits and Operating Hours:**  
    Modify factors like modal split percentages, gate operating hours, train schedules, and yard stacking limits to reflect different operational conditions.

# Notes on UI
- Regarding Ship Schedules: The expected arrival column is treated as a number of hours. When you add a ship to the schedule, the code multiplies the value by 60 to convert it to minutes. For example, if the value is 5, the simulation stores it as 300 minutes, meaning the ship is expected to arrive 5 hours after the simulation starts.

# Notes on how containers are tracked

Only containers coming from vessels are tracked for dwell time. The simulation marks these with a flag (e.g., container.from_vessel = True). Containers that are already in the yard when the simulation starts (initial yard containers) are not tracked for dwell time.

Each component has a clearly defined start and end point, and the times are measured in minutes (later converted to hours or days for display).
- Ship Waiting (Schedule Delay):
  - Start: When the ship is scheduled to arrive. The expected arrival time is provided (in hours) and converted to minutes.
  - End: When the ship actually arrives. The actual arrival is determined by applying a variability factor (using a normal distribution) to the expected time.
  - Logged As: The difference between actual and expected arrival times is recorded as the ship arrival delay.
- Berth Queue Time:
  - Start: When the ship requests a berth upon arriving at the port.
  - End: When the ship is assigned a berth (recorded as the berth entry time).
  - Logged As: The time difference between the start of the berth request and the actual berth entry time.
- Unloading Process:
  - Start: When the ship docks and container unloading begins using cranes.
  - End: When a container is unloaded and enters the yard (i.e., when its yard entry time is recorded).
  - Logged As: The difference between the ship’s berth entry time and the container’s yard entry time, representing the time taken for unloading.
- Yard Storage Time:
  - Start: Immediately after a container is unloaded into the yard.
  - End: When the container’s scheduled yard waiting period ends (this period is determined by a normal distribution with a minimum of one hour).
  - Logged As: The predetermined waiting time before the container is ready for departure.
- Stacking Retrieval:
  - Start: When a container becomes ready for departure and the process to retrieve it from its stack begins.
  - End: After the retrieval process completes, which takes a base time plus additional time based on the container’s stacking level (and adjusted by a congestion factor).
  - Logged As: The calculated retrieval time is recorded using a dedicated logging call.
- Inland Transport Wait:
  - Start: Once the stacking retrieval is finished, the container enters a waiting period for the gate to process its departure (whether by truck or train).
  - End: When the container finally departs (i.e., when the gate processes its departure).
  - Logged As: The wait time is measured as the difference between the time when departure processing starts and when it completes.

# Additional Assumptions NYNJ-specific inputs
- Number of Berth Spaces: APM Terminal has a quay length of approximately 6,000 feet (1,828 meters), divided into multiple berths. Based on the infrastructure and operational capacity, the terminal can berth 3 Ultra-Large Container Ships (ULCS) simultaneously.
- Cranes per Berth: The terminal currently operates 14 cranes, including 10 Super Post-Panamax cranes with a 23-container outreach. With three berths for ULCS, this equates to an average of approximately 4-5 cranes per berth. The distribution assumes an even allocation of cranes across the berths. [Source1](https://container-news.com/apm-terminals-elizabeth-enhances-operations-with-new-container-cranes/), [Source2](https://www.porttechnology.org/news/apm_terminals_elizabeth_welcomes_new_cranes/)
- Trains per day: APM Terminals Elizabeth schedules four outbound train departures daily to the Midwest from its intermodal rail facility. [Source](https://www.apmterminals.com/en/port-elizabeth/about/our-terminal)
- Rail capacity: U.S. intermodal trains are designed for double-stacking containers, with each railcar holding two 40-foot containers (or 4 TEUs). Assuming a train length of 100 to 125 railcars, this results in about 200 to 250 containers per train.
- Default Gate Operating Hours: Gates operate from 6:00 AM to 5:00 PM, Monday through Friday.
- Weekends: No official information is provided for Saturday and Sunday operations, so it is assumed the gates are closed on weekends unless special arrangements are made.
- Gate Capacity: The gate system is designed to handle up to 2,500 truck movements per day. [Source](https://www.hub.com.pa/propelling-safety-standards-upwards-at-apm-terminals-port-elizabeth/)