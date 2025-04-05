import random
import math

class Container:
    """
    Represents a container with processing checkpoints, including its type.
    Now also tracks its assigned stack (stack_index) and level within the stack (stack_level).
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
    Manages container storage for a specific container type with capacity constraints and stacking logic.
    
    The yard is divided into a number of stacks. Containers are added sequentially:
    first filling level 1 in all stacks, then level 2, etc. Each container is assigned a stack index
    and a level within that stack. The yard computes positioning delays based on level and retrieval delays
    based on the number of moves required to retrieve a container.
    
    Retrieval moves: For a container at level L in a stack of height H,
    moves = 2*(H - L) + 1 (i.e. move out all containers above, retrieve target, then move back the others)
    """
    def __init__(self, capacity, initial_count, max_stacking, base_positioning_time,
                 positioning_penalty, base_retrieval_time, moving_penalty):
        self.capacity = capacity
        self.max_stacking = max_stacking
        self.base_positioning_time = base_positioning_time
        self.positioning_penalty = positioning_penalty
        self.base_retrieval_time = base_retrieval_time
        self.moving_penalty = moving_penalty
        
        # Compute number of stacks available in the yard.
        self.num_stacks = capacity // max_stacking  # using integer division
        self.stacks = [[] for _ in range(self.num_stacks)]
        
        # Pre-fill the yard with initial_count containers.
        # Containers are added sequentially: fill each stack's level 1, then level 2, etc.
        for i in range(initial_count):
            stack_index = i % self.num_stacks
            # If the chosen stack is full, try to find an alternate stack.
            if len(self.stacks[stack_index]) >= self.max_stacking:
                found = False
                for idx, stack in enumerate(self.stacks):
                    if len(stack) < self.max_stacking:
                        stack_index = idx
                        found = True
                        break
                if not found:
                    print("WARNING: Unable to fill initial container; yard is full.")
                    break
            container = Container("Initial", None, None, random.choice(['Rail', 'Road']), None)
            container.entered_yard = 0
            container.stack_index = stack_index
            container.stack_level = len(self.stacks[stack_index]) + 1
            self.stacks[stack_index].append(container)
    
    def add_container(self, container):
        """
        Adds a container to the first available stack (following sequential, level-by-level filling).
        Returns (True, positioning_delay) if successful; otherwise, returns (False, None).
        """
        for i, stack in enumerate(self.stacks):
            if len(stack) < self.max_stacking:
                container.stack_index = i
                container.stack_level = len(stack) + 1
                # Compute positioning delay: base time + penalty per level above ground.
                positioning_delay = self.base_positioning_time + (container.stack_level - 1) * self.positioning_penalty
                stack.append(container)
                return True, positioning_delay
        print(f"WARNING: Yard capacity ({self.capacity}) reached, container not added")
        return False, None

    def remove_container(self, container):
        """
        Removes a container from its assigned stack.
        Computes retrieval delay based on the number of moves required:
          retrieval_moves = 2*(H - L) + 1, where H = current stack height and L = container's level.
        After removal, containers above are shifted down.
        Returns (True, retrieval_delay) if removal is successful; otherwise, (False, None).
        """
        idx = container.stack_index
        if idx is None or idx >= len(self.stacks):
            return False, None
        
        stack = self.stacks[idx]
        if container not in stack:
            return False, None
        
        H = len(stack)
        L = container.stack_level
        retrieval_moves = 2 * (H - L) + 1
        retrieval_delay = self.base_retrieval_time + retrieval_moves * self.moving_penalty
        
        # Remove the container from the stack.
        stack.pop(L - 1)
        # Update levels for containers that were above the removed container.
        for i in range(L - 1, len(stack)):
            stack[i].stack_level = i + 1
        return True, retrieval_delay

    def is_full(self):
        """Returns True if all stacks are full."""
        for stack in self.stacks:
            if len(stack) < self.max_stacking:
                return False
        return True

    def reorganize_yard(self):
        """
        Placeholder for future yard reorganization logic.
        Currently, no reorganization is performed.
        """
        pass
