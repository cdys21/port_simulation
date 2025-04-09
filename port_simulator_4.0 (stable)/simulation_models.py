#simulation_models.py
import random, math

class Container:
    """
    Represents a container with processing checkpoints, including its type.
    """
    def __init__(self, vessel_name, vessel_scheduled_arrival, vessel_arrives, mode, container_type):
        self.vessel = vessel_name
        self.vessel_scheduled_arrival = vessel_scheduled_arrival
        self.vessel_arrives = vessel_arrives
        self.vessel_berths = None
        self.entered_yard = None
        self.waiting_for_inland_tsp = None
        self.loaded_for_transport = None
        self.departed_port = None
        self.mode = mode  # 'Rail' or 'Road'
        self.container_type = container_type  # e.g., 'Standard', 'Reefer', 'Hazardous'

class Vessel:
    """
    Represents a vessel arriving at the port carrying containers.
    container_counts is a dict mapping container type to count.
    container_type_params provides type-specific parameters.
    """
    def __init__(self, env, name, container_counts, day, hour, container_type_params):
        self.env = env
        self.name = name
        self.container_counts = container_counts
        self.scheduled_arrival = (day - 1) * 24 + hour
        self.actual_arrival = self.scheduled_arrival + random.triangular(-1, 5, 2)
        self.vessel_berths = None
        self.containers = []
        for container_type, count in container_counts.items():
            rail_percentage = container_type_params[container_type]['rail_percentage']
            for _ in range(count):
                mode = random.choices(['Rail', 'Road'],
                                      weights=[rail_percentage, 1 - rail_percentage])[0]
                self.containers.append(
                    Container(
                        self.name,
                        self.scheduled_arrival,
                        self.actual_arrival,
                        mode,
                        container_type
                    )
                )

class Yard:
    """
    Simplified Yard model that treats the yard as a flat container list
    without any stacking logic or delays based on container position.
    """
    def __init__(self, capacity, initial_count):
        self.capacity = capacity
        self.containers = []

        for _ in range(initial_count):
            container = Container("Initial", None, None, random.choice(['Rail', 'Road']), None)
            container.entered_yard = 0
            self.containers.append(container)

    def add_container(self, container):
        """
        Adds a container to the yard if there is available capacity.
        Returns (True, positioning_delay) if successful; otherwise (False, None).
        """
        if len(self.containers) >= self.capacity:
            print(f"WARNING: Yard capacity ({self.capacity}) reached, container not added")
            return False, None
        self.containers.append(container)
        positioning_delay = 0.05  # Use a constant positioning delay
        return True, positioning_delay

    def remove_container(self, container):
        """
        Removes the container from the yard.
        Returns (True, retrieval_delay) if successful; otherwise (False, None).
        """
        if container not in self.containers:
            return False, None
        self.containers.remove(container)
        retrieval_delay = 0.1  # Use a constant retrieval delay
        return True, retrieval_delay
