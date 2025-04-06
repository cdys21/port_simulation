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
        # New attributes for stacking
        self.stack_index = None
        self.stack_level = None

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
    Manages container storage for a specific container type with capacity constraints and stacking.
    The yard is divided into stacks. Containers are added to the stack with the lowest height.
    The positioning delay is based on the container's level in its stack.
    When retrieving a container, the delay is based on the number of containers above it.
    """
    def __init__(self, capacity, initial_count, max_stacking=5,
                 base_positioning_time=0.05, positioning_penalty=0.02,
                 base_retrieval_time=0.1, moving_penalty=0.03):
        self.capacity = capacity
        self.max_stacking = max_stacking
        self.base_positioning_time = base_positioning_time
        self.positioning_penalty = positioning_penalty
        self.base_retrieval_time = base_retrieval_time
        self.moving_penalty = moving_penalty
        # Determine number of stacks; assume capacity is the total number of containers allowed.
        self.num_stacks = capacity // max_stacking  
        self.stacks = [[] for _ in range(self.num_stacks)]
        
        # Pre-fill the yard with initial_count containers.
        for i in range(initial_count):
            placed = False
            for s in range(self.num_stacks):
                if len(self.stacks[s]) < self.max_stacking:
                    container = Container("Initial", None, None, random.choice(['Rail', 'Road']), None)
                    container.entered_yard = 0
                    container.stack_index = s
                    container.stack_level = len(self.stacks[s]) + 1
                    self.stacks[s].append(container)
                    placed = True
                    break
            if not placed:
                print("WARNING: Yard is full during initial fill.")
                break

    def add_container(self, container):
        """
        Attempts to add the container to the yard.
        Returns (True, positioning_delay) if successful; otherwise (False, None).
        """
        if all(len(stack) >= self.max_stacking for stack in self.stacks):
            print(f"WARNING: Yard capacity ({self.capacity}) reached, container not added")
            return False, None
        # Find the stack with the minimum height that is not full.
        candidate_index = None
        min_height = self.max_stacking + 1
        for idx, stack in enumerate(self.stacks):
            if len(stack) < self.max_stacking and len(stack) < min_height:
                candidate_index = idx
                min_height = len(stack)
        if candidate_index is None:
            print("WARNING: No available stack found.")
            return False, None
        container.stack_index = candidate_index
        container.stack_level = len(self.stacks[candidate_index]) + 1
        self.stacks[candidate_index].append(container)
        positioning_delay = self.base_positioning_time + (container.stack_level - 1) * self.positioning_penalty
        return True, positioning_delay

    def remove_container(self, container):
        """
        Removes the container from its stack.
        Computes retrieval delay based on how many containers are above it.
        Returns (True, retrieval_delay) if removal is successful; otherwise (False, None).
        """
        if container.stack_index is None or container.stack_index >= len(self.stacks):
            return False, None
        stack = self.stacks[container.stack_index]
        if container not in stack:
            return False, None
        pos = stack.index(container)  # 0-indexed; top container is at the end.
        # Number of containers above:
        num_above = len(stack) - pos - 1
        retrieval_delay = self.base_retrieval_time + num_above * self.moving_penalty
        stack.pop(pos)
        # Update levels for remaining containers in the stack.
        for i, cont in enumerate(stack):
            cont.stack_level = i + 1
        return True, retrieval_delay
