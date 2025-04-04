# Port Simulation Project

## Overview

This project simulates maritime port operations focused on the movement of import containers. The simulation models container arrival, unloading, and departures via road (truck) and rail (train), collecting metrics to analyze port performance.

## Directory Structure
```
port_simulation/
├── config/
│   └── config.yaml         # All simulation parameters and distribution settings
├── simulation/
│   ├── __init__.py         # Package initializer for the simulation modules
│   ├── models.py           # Domain entities (Container, Vessel, Yard)
│   ├── processes.py        # All simulation processes (vessel arrival, unloading, departures, monitoring, etc.)
│   ├── metrics.py          # Functions for metrics collection and conversion to DataFrame
│   └── simulation_runner.py# Core simulation engine that connects models, processes, and metrics
├── ui/
│   ├── __init__.py         # Package initializer for the UI module
│   └── dashboard.py        # Streamlit dashboard for scenario inputs and results visualization
├── main.py                 # Entry point for running the simulation from the command line
├── requirements.txt        # Python dependencies
└── README.md               # Project overview and instructions
```

## Setup Instructions

1. **Clone the Repository:**
```bash
   git clone <repository_url>
   cd port_simulation
   ```
2. **Create a Virtual Environment (Optional):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

# Running the Simulation
## Command Line
Run the simulation using the main entry point:
```bash
python main.py
```
This loads the default configuration from config/config.yaml and runs the simulation. Summary metrics are printed to the console.

# Streamlit Dashboard
To launch the dashboard for an interactive UI:
```bash
streamlit run ui/dashboard.py
```
This opens a web-based dashboard where you can modify simulation parameters, run the simulation, and visualize results.

# Configuration
All simulation parameters are managed in config/config.yaml. You can adjust:
- Port parameters (e.g., number of berths, yard capacity)
- Process parameters (e.g., distributions for arrival times, unloading times)
- Operational policies (e.g., rail adoption rate, gate opening rules)
- Vessel schedules and container counts

# Contributing
Contributions are welcome. Please maintain the modular structure when adding new features or making changes.

# License
This project is licensed under the MIT License.

## How to Run the Project

1. **Set Up Your Environment:**
- Create and activate a virtual environment (optional but recommended).
- Install dependencies:
```bash
pip install -r requirements.txt
```

2. **Run from the Command Line:**
Execute the main script:
```bash
python main.py
```