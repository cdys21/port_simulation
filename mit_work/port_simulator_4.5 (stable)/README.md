# Container Terminal Simulation

This project simulates the flow of containers through a terminal—from vessel arrival to departure via inland transportation. The simulation tracks various checkpoints such as unloading, yard occupancy, and departures. It supports multiple container types (e.g., Standard, Reefer, Hazardous) with type-specific parameters for unloading time, transportation mode distribution, and truck process times.

The simulation logic is implemented using SimPy, and interactive visualizations are built with Plotly in a Streamlit UI.

## Folder Structure
```python
my_simulation/
├── config.py # Default configuration (modifiable via UI)
├── simulation_models.py # Core data models (Container, Vessel, Yard)
├── simulation_processes.py # Simulation logic and monitoring functions
├── streamlit_app.py # Streamlit UI that runs the simulation and displays charts
└── README.md # This file
```

## Features

- **Multiple Container Types:**  
  Each container type has its own yard with separate capacity, unloading time, transportation mode probabilities, and truck process times.

- **Dynamic Configuration:**  
  The entire simulation configuration is modifiable through a JSON text area in the Streamlit UI. You can change vessel parameters, yard capacities, and more.

- **Progress Bar:**  
  The simulation is run in one-hour increments and updates a progress bar in real time.

- **Interactive Visualizations:**  
  Visuals include:
  - Total yard occupancy over time.
  - Yard occupancy per container category with horizontal capacity lines.
  - Cumulative unloaded containers over time (overall and per container type).
  - Cumulative departures over time (by mode and per container type).
  - Dwell time distributions using boxplots (overall, by container type, and by transportation mode).

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/container-terminal-simulation.git
cd container-terminal-simulation
```

2. **Create and activate a virtual environment (optional but recommended):**
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```
If a requirements.txt file is not provided, install the following packages:
```bash
pip install simpy pandas plotly streamlit
```

## Usage
To launch the Streamlit UI, run the following command in the project directory:

```bash
streamlit run streamlit_app.py
```
This will open a browser window with the Container Terminal Simulation Dashboard. You can modify the simulation configuration on the sidebar, click Run Simulation, and view the real-time progress along with interactive charts of simulation outputs.

## Configuration
The default simulation parameters are stored in the config.py file. The UI loads these defaults as JSON, which you can modify before running the simulation. Parameters include:
- **Berth Count & Gate Count:** Define the number of berths and gates available at the terminal.
- **Simulation Duration:** Total simulation time (in hours).
- **Container Types:** Each type (e.g., Standard, Reefer, Hazardous) has:
    - Yard capacity and initial fill percentage.
    - Rail percentage (probability that a container is assigned to rail).
    - Unload time parameters (tuple: low, high, mode).
    - Truck process time parameters (tuple: low, high, mode).
- **Vessel Data:** A list of vessels with attributes such as vessel name, container counts (by type), day, and hour of arrival.
All these parameters can be modified via the JSON text area in the UI.

## License

This project is licensed under the MIT License. See the LICENSE file for details.