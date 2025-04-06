# simulation/models.py
import random

class Container:
    """Represents a container with checkpoint timestamps."""
    def __init__(self, vessel_name, vessel_scheduled_arrival, vessel_arrives, mode):
        self.vessel = vessel_name
        self.vessel_scheduled_arrival = vessel_scheduled_arrival
        self.vessel_arrives = vessel_arrives
        self.vessel_berths = None
        self.entered_yard = None
        self.waiting_for_inland_tsp = None
        self.loaded_for_transport = None
        self.departed_port = None
        self.mode = mode  # 'Rail' or 'Road'

class Vessel:
    """Represents a vessel carrying containers."""
    def __init__(self, env, name, container_count, day, hour, arrival_params, rail_adoption):
        self.env = env
        self.name = name
        self.container_count = container_count
        self.scheduled_arrival = (day - 1) * 24 + hour
        # Calculate actual arrival using a triangular distribution
        min_offset = arrival_params.get('min_offset', -1)
        max_offset = arrival_params.get('max_offset', 5)
        mode_val = arrival_params.get('mode', 2)
        self.actual_arrival = self.scheduled_arrival + random.triangular(min_offset, max_offset, mode_val)
        self.vessel_berths = None
        self.containers = []
        for _ in range(container_count):
            mode_choice = random.choices(['Rail', 'Road'], weights=[rail_adoption, 1 - rail_adoption])[0]
            container = Container(self.name, self.scheduled_arrival, self.actual_arrival, mode_choice)
            self.containers.append(container)

class Yard:
    """Manages container storage with capacity constraints.
    Now starts empty; containers will be added only via vessel arrivals.
    """
    def __init__(self, capacity):
        self.capacity = capacity
        self.containers = []  # Start empty

    def add_container(self, container):
        if len(self.containers) >= self.capacity:
            print(f"WARNING: Yard capacity ({self.capacity}) exceeded. Container not added.")
            return False
        self.containers.append(container)
        return True

    def remove_container(self, container):
        if container in self.containers:
            self.containers.remove(container)
            return True
        return False
