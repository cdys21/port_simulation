# yard.py

import simpy
from container import Container

class Yard:
    """
    Represents a yard for storing containers.
    
    Attributes:
        env (simpy.Environment): The simulation environment.
        capacity (int): Maximum number of containers the yard can hold.
        max_stack_height (int): Maximum stacking height allowed.
        retrieval_delay_per_move (float): Delay (in hours) per level movement when retrieving a container.
        containers (list): List of containers currently in the yard.
    """
    def __init__(self, env, capacity, max_stack_height, retrieval_delay_per_move=0.1, initial_container_count=0):
        self.env = env
        self.capacity = capacity
        self.max_stack_height = max_stack_height
        self.retrieval_delay_per_move = retrieval_delay_per_move
        self.containers = []
        # Calculate containers per stacking level.
        self.per_level = capacity // max_stack_height
        
        # Pre-populate with initial containers.
        for i in range(initial_container_count):
            container = Container(container_id=i, is_initial=True)
            # Record yard entry and retrieval ready time for initial containers.
            container.checkpoints["entered_yard"] = self.env.now
            container.checkpoints["retrieval_ready"] = self.env.now
            container.checkpoints["vessel"] = "Initial"
            self.add_container(container)
    
    def add_container(self, container):
        """
        Add a container to the yard and assign its stacking level.
        
        Args:
            container (Container): The container to add.
        
        Raises:
            Exception: If the yard is full.
        """
        if len(self.containers) >= self.capacity:
            raise Exception("Yard is full. Cannot add more containers.")
        # Assign stacking level based on current occupancy.
        container.stacking_level = len(self.containers) // self.per_level
        self.containers.append(container)
    
    def get_occupancy(self):
        """
        Return the current number of containers in the yard.
        """
        return len(self.containers)
    
    def retrieve_ready_container(self):
        """
        Retrieve the container that is ready to depart.
        A container is considered ready if the current time is greater than or equal to its
        'retrieval_ready' checkpoint. Before returning, a retrieval delay based on the container's
        stacking level is applied.
        
        Yields:
            simpy.timeout: Delay for waiting or retrieval delay.
        
        Returns:
            Container: The retrieved container, with its 'waiting_for_inland_tsp' checkpoint recorded.
        """
        while True:
            # Filter containers that are ready for retrieval.
            ready_containers = [c for c in self.containers 
                                if "retrieval_ready" in c.checkpoints and self.env.now >= c.checkpoints["retrieval_ready"]]
            if ready_containers:
                # Select the container with the earliest retrieval_ready time.
                container = min(ready_containers, key=lambda c: c.checkpoints["retrieval_ready"])
                self.containers.remove(container)
                retrieval_delay = (self.max_stack_height - 1 - container.stacking_level) * self.retrieval_delay_per_move
                yield self.env.timeout(retrieval_delay)
                container.checkpoints["waiting_for_inland_tsp"] = self.env.now
                return container
            else:
                # If no container is ready, wait until the next retrieval_ready time.
                if self.containers:
                    next_ready_time = min(c.checkpoints["retrieval_ready"] for c in self.containers if "retrieval_ready" in c.checkpoints)
                    wait_time = next_ready_time - self.env.now
                    yield self.env.timeout(wait_time)
                else:
                    return None
