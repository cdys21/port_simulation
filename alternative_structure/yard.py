import random
random.seed(42)

import simpy
import math

class Container:
    """
    Represents a container stored in the yard.
    
    Attributes:
        container_id (int): Unique identifier.
        category (str): Container category (default "ANY").
        arrival_time (float): Time when container arrived in the yard.
        storage_duration (float): Planned waiting period in the yard.
        stacking_level (int): The stacking level assigned in the yard.
        is_initial (bool): True if the container was present at simulation start.
    """
    def __init__(self, container_id, category="ANY", arrival_time=0.0, storage_duration=0.0, is_initial=False):
        self.container_id = container_id
        self.category = category
        self.arrival_time = arrival_time
        self.storage_duration = storage_duration
        self.stacking_level = None  # To be assigned upon addition to the yard
        self.is_initial = is_initial

    def __str__(self):
        init_str = "Initial" if self.is_initial else "Arrived"
        return (f"Container(id={self.container_id}, category={self.category}, "
                f"{init_str}, arrival_time={self.arrival_time}, storage_duration={self.storage_duration:.2f}, "
                f"stacking_level={self.stacking_level})")


class Yard:
    """
    Represents a yard for storing containers of a specific category.
    
    Attributes:
        env (simpy.Environment): The simulation environment.
        capacity (int): Maximum number of containers in the yard.
        max_stack_height (int): Maximum stacking height.
        retrieval_delay_per_move (float): Delay (in hours) per level movement when retrieving a container.
        containers (list): List of stored containers (order of addition, not necessarily retrieval order).
    """
    def __init__(self, env, capacity, max_stack_height, retrieval_delay_per_move=0.1):
        self.env = env
        self.capacity = capacity
        self.max_stack_height = max_stack_height
        self.retrieval_delay_per_move = retrieval_delay_per_move
        self.containers = []  # Containers are stored as they are added.
        
        # Calculate how many containers can be placed per stacking level.
        self.per_level = self.capacity // self.max_stack_height

    def add_container(self, container):
        """
        Add a container to the yard and assign it a stacking level based on current occupancy.
        Raises an exception if the yard is full.
        """
        if len(self.containers) >= self.capacity:
            raise Exception("Yard is full. Cannot add more containers.")
        container.stacking_level = len(self.containers) // self.per_level
        self.containers.append(container)
        print(f"Time {self.env.now}: Added {container}")

    def get_occupancy(self):
        """
        Return the current number of containers in the yard.
        """
        return len(self.containers)
    
    def retrieve_ready_container(self):
        """
        Retrieve the container that is ready to depart.
        
        The logic is:
          - A container is considered ready if current time ≥ (arrival_time + storage_duration).
          - Among all ready containers, the one with the earliest completion time is selected.
          - If no container is ready, the process waits until the next container finishes waiting.
        
        After selecting a container, a retrieval delay is applied based on its stacking level:
          retrieval_delay = (max_stack_height - 1 - stacking_level) * retrieval_delay_per_move
        
        Yields:
            simpy.timeout for waiting (if needed) and retrieval delay.
        Returns:
            The retrieved container.
        """
        while True:
            # Find all containers whose waiting period is over.
            ready_containers = [c for c in self.containers if self.env.now >= (c.arrival_time + c.storage_duration)]
            if ready_containers:
                # Select the container with the earliest ready time.
                container = min(ready_containers, key=lambda c: c.arrival_time + c.storage_duration)
                self.containers.remove(container)
                retrieval_delay = (self.max_stack_height - 1 - container.stacking_level) * self.retrieval_delay_per_move
                yield self.env.timeout(retrieval_delay)
                return container
            else:
                # No container is ready; wait until the next one becomes ready.
                if self.containers:
                    next_ready_time = min(c.arrival_time + c.storage_duration for c in self.containers)
                    wait_time = next_ready_time - self.env.now
                    yield self.env.timeout(wait_time)
                else:
                    return None


# Testing the updated Yard module.
if __name__ == '__main__':
    # Set seed for reproducibility.
    random.seed(42)
    
    # Create a SimPy environment.
    env = simpy.Environment()
    
    # Configure the yard.
    capacity = 40
    max_stack_height = 4    # E.g., 4 levels, so if capacity is 40 then 10 containers per level.
    retrieval_delay_per_move = 10/60  # in hours (6 minutes) per level move.
    
    yard = Yard(env, capacity, max_stack_height, retrieval_delay_per_move)
    
    # Add preexisting (initial) containers with storage_duration = 0 (they're ready immediately).
    num_initial = 10
    for i in range(num_initial):
        container = Container(container_id=i, arrival_time=env.now, storage_duration=0, is_initial=True)
        yard.add_container(container)
    
    # Add containers arriving via vessels with random storage times.
    num_arriving = 5
    storage_mean = 5
    storage_stdev = 1
    for i in range(num_initial, num_initial + num_arriving):
        storage_duration = max(0, random.normalvariate(storage_mean, storage_stdev))
        container = Container(container_id=i, arrival_time=env.now, storage_duration=storage_duration)
        yard.add_container(container)
    
    def retrieval_process(env, yard):
        while yard.get_occupancy() > 0:
            container = yield env.process(yard.retrieve_ready_container())
            if container is not None:
                status = "Initial" if container.is_initial else "Arrived"
                print(f"Time {env.now:.2f}: Retrieved container {container.container_id} ({status})")
    
    # Start the retrieval process.
    env.process(retrieval_process(env, yard))
    env.run()