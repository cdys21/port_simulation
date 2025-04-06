# models.py
import random
import pandas as pd

class Container:
    def __init__(self, id, arrival_time, container_types, modal_split):
        self.id = id
        self.arrival_time = arrival_time
        self.is_new = True  # Only track dwell times for new containers

        # Determine container type with slight variation in probability.
        reefer_prob = max(
            0,
            min(1, random.normalvariate(
                container_types["reefer"]["probability"],
                container_types["reefer"]["probability"] * 0.1
            ))
        )
        self.type = 'reefer' if random.random() < reefer_prob else 'dry'

        # Determine modal with slight variation.
        train_prob = max(
            0,
            min(1, random.normalvariate(
                modal_split["train"],
                modal_split["train"] * 0.067
            ))
        )
        self.modal = 'train' if random.random() < train_prob else 'truck'

        self.yard_entry_time = None
        self.ready_time = None
        self.departure_time = None
        self.stacking_level = None  # For tracking stacking level
        self.from_vessel = True  # Container will be tracked (not from yard)
        self.departure_wait_start = None  # Time when departure wait started

        # Compute yard waiting time (converted from days to minutes)
        if self.type == 'reefer':
            yard_waiting_time = random.normalvariate(
                container_types["reefer"]["yard_waiting_time"]["mean"],
                container_types["reefer"]["yard_waiting_time"]["std"]
            ) * 24 * 60
        else:
            yard_waiting_time = random.normalvariate(
                container_types["dry"]["yard_waiting_time"]["mean"],
                container_types["dry"]["yard_waiting_time"]["std"]
            ) * 24 * 60

        self.yard_waiting_time = max(60, yard_waiting_time)  # Minimum waiting time: 1 hour
        self.berth_time = None  # Time when vessel carrying container berthed

class Ship:
    def __init__(self, env, name, container_count, expected_arrival, actual_arrival, container_types, modal_split):
        self.env = env
        self.name = name
        self.id = name  # Keeping id for compatibility
        self.container_count = container_count
        self.container_types = container_types
        self.modal_split = modal_split
        self.expected_arrival = expected_arrival  # in minutes from simulation start
        self.actual_arrival = actual_arrival      # in minutes from simulation start
        self.berth_entry_time = None
        self.departure_time = None
        self.containers = self._generate_containers()

    def _generate_containers(self):
        containers = []
        for i in range(self.container_count):
            containers.append(Container(
                f"{self.id}_container_{i}",
                self.env.now,
                self.container_types,
                self.modal_split
            ))
        return containers

class ShipSchedule:
    def __init__(self):
        self.ships = []

    def add_ship(self, name, containers, expected_arrival):
        """Add a ship with expected arrival in hours (converted to minutes)"""
        # Ensure expected_arrival is valid; if not, assign a default (e.g., 1 hour)
        if expected_arrival is None:
            pass
        else:
            self.ships.append({
                "name": name,
                "containers": containers,
                "expected_arrival": expected_arrival * 60  # converting hours to minutes
            })

    def get_dataframe(self):
        """Return the schedule as a pandas DataFrame"""
        return pd.DataFrame(self.ships)

    def clear(self):
        """Clear the schedule"""
        self.ships = []