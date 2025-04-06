# main.py
from simulation.simulation_runner import load_config, run_simulation

def main():
    config = load_config()
    df, metrics = run_simulation(config)
    print("Simulation completed. See the summary above.")

if __name__ == '__main__':
    main()
