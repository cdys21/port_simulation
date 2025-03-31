# config.py
import datetime

# Default ship schedule in hours (expected arrival) and container counts
DEFAULT_SHIPS_SCHEDULE = [
    {"name": "CEZANNE", "containers": 2642, "expected_arrival": 8},
    {"name": "CCNI ANDES", "containers": 2338, "expected_arrival": 10},
    {"name": "CMA CGM LEO", "containers": 2187, "expected_arrival": 14},
    {"name": "ONE REINFORCEMENT", "containers": 1752, "expected_arrival": 15},
    {"name": "POLAR ECUADOR", "containers": 1431, "expected_arrival": 16},

    {"name": "W KITHIRA", "containers": 1311, "expected_arrival": 6+24},
    {"name": "MAERSK ATHABASCA", "containers": 998, "expected_arrival": 8+24},
    {"name": "MAERSK SENTOSA", "containers": 896, "expected_arrival": 8+24},
    {"name": "MAERSK MONTE LINZOR", "containers": 892, "expected_arrival": 12+24},
    {"name": "SUAPE EXPRESS", "containers": 1062, "expected_arrival": 15+24}
]


ARRIVAL_TIME_VARIABILITY = {"mean": 0.0, "std": 0.0}  # hours

MAX_BERTHS_DEFAULT = 4
CRANES_PER_BERTH_DEFAULT = 4
CONTAINER_UNLOAD_TIME_DEFAULT = {"mean": 2.5, "std": 0.5}  # minutes
BERTH_TRANSITION_TIME_DEFAULT = 60  # minutes

CONTAINER_TYPES_DEFAULT = {
    "dry": {
        "probability": 0.95,
        "yard_waiting_time": {"mean": 0, "std": 1.5}  # days
    },
    "reefer": {
        "probability": 0.05,
        "yard_waiting_time": {"mean": 0, "std": 0.8}  # days
    }
}

MODAL_SPLIT_DEFAULT = {"truck": 0.85, "train": 0.15}

GATE_HOURS_DEFAULT = {
    "open": 6,
    "close": 17,
    "gates_capacity": 125,
    "truck_pickup_time": 15,  # minutes
    "containers_per_truck": 2
}

TRAIN_SCHEDULE_DEFAULT = {"trains_per_day": 6, "capacity": 500}

# Stacking parameters
MAX_STACKING_HEIGHT_DEFAULT = 4
STACKING_RETRIEVAL_BASE_TIME_DEFAULT = 15 # minutes
STACKING_RETRIEVAL_FACTOR_DEFAULT = 5 # minutes per container

# Optional simulation start (if needed)
SIMULATION_START_DEFAULT = datetime.datetime(2025, 1, 1, 6, 0)