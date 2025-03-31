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
    """
    def __init__(self, container_id, category="ANY", arrival_time=0.0, storage_duration=0.0):
        self.container_id = container_id
        self.category = category
        self.arrival_time = arrival_time
        self.storage_duration = storage_duration # hours
        self.stacking_level = None  # Will be assigned upon adding to the yard

    def __str__(self):
        return (f"Container(id={self.container_id}, category={self.category}, "
                f"arrival_time={self.arrival_time}, storage_duration={self.storage_duration:.2f}, "
                f"stacking_level={self.stacking_level})")


class Yard:
    """
    Represents a yard for storing containers of a specific category.
    
    Attributes:
        env (simpy.Environment): The simulation environment.
        capacity (int): Maximum number of containers in the yard.
        max_stack_height (int): Maximum stacking height.
        retrieval_delay_per_move (float): Delay per level movement when retrieving a container.
        containers (list): FIFO list of stored containers.
    """
    def __init__(self, env, capacity, max_stack_height, retrieval_delay_per_move=0.1):
        self.env = env
        self.capacity = capacity
        self.max_stack_height = max_stack_height
        self.retrieval_delay_per_move = retrieval_delay_per_move # hours
        self.containers = []  # List to store containers in FIFO order
        
        # Determine how many containers can be stored per stacking level.
        self.per_level = self.capacity // self.max_stack_height

    def add_container(self, container):
        """
        Add a container to the yard, assigning a stacking level based on current occupancy.
        Raises an exception if the yard is full.
        """
        if len(self.containers) >= self.capacity:
            raise Exception("Yard is full. Cannot add more containers.")
        # Determine stacking level: based on the current count divided by the per-level capacity.
        container.stacking_level = len(self.containers) // self.per_level
        self.containers.append(container)
        print(f"Time {self.env.now}: Added {container}")

    def get_occupancy(self):
        """
        Return the current number of containers in the yard.
        """
        return len(self.containers)
    
    def retrieve_next_container(self):
        """
        Retrieve the next container in FIFO order.
        Simulates the retrieval delay based on the container's stacking level.
        
        Yields:
            env.timeout for the retrieval delay.
        
        Returns:
            The retrieved container.
        """
        if not self.containers:
            raise Exception("Yard is empty. No container to retrieve.")
        
        # Retrieve the first container (FIFO).
        container = self.containers.pop(0)
        
        # Compute retrieval delay:
        # Delay = (max_stack_height - 1 - stacking_level) * retrieval_delay_per_move
        retrieval_delay = (self.max_stack_height - 1 - container.stacking_level) * self.retrieval_delay_per_move
        yield self.env.timeout(retrieval_delay)
        return container
    
    def process_container(self, container):
        """
        Process a container: wait for its planned storage duration, then retrieve it.
        
        Yields:
            env.timeout for storage duration and retrieval delay.
        
        Returns:
            The container after processing.
        """
        # Wait for the container's storage duration.
        yield self.env.timeout(container.storage_duration)
        # Retrieve the container (simulate retrieval delay).
        retrieved = yield self.env.process(self.retrieve_next_container())
        return retrieved


# Testing the Yard module.
if __name__ == '__main__':
    # Set seed for reproducibility.
    random.seed(42)
    
    # Create a SimPy simulation environment.
    env = simpy.Environment()
    
    # Yard configuration: capacity 40, max stacking height 4 (i.e., 10 containers per level), and a retrieval delay of 0.1 per move.
    capacity = 40
    max_stack_height = 4
    retrieval_delay_per_move = 0.1 # hours
    
    yard = Yard(env, capacity, max_stack_height, retrieval_delay_per_move)
    
    # Normal distribution parameters for container storage time.
    storage_mean = 5 # hours
    storage_stdev = 1 # hours
    
    # Create and add 30 containers.
    for i in range(30):
        # Ensure storage duration is non-negative.
        storage_duration = max(0, random.normalvariate(storage_mean, storage_stdev))
        container = Container(container_id=i, arrival_time=env.now, storage_duration=storage_duration)
        yard.add_container(container)
    
    def container_process(env, yard, container):
        print(f"Time {env.now}: Processing container {container.container_id}")
        retrieved_container = yield env.process(yard.process_container(container))
        print(f"Time {env.now}: Retrieved container {retrieved_container.container_id}")
    
    # Launch processes for the first 30 containers.
    # (Note: As containers are processed in FIFO order, these processes will effectively process the containers one by one.)
    for i in range(30):
        # Retrieve container from the current yard state.
        # For testing, we directly start a process for the container at the front.
        # In a full simulation, container processing would be scheduled according to departure events.
        container = yard.containers[i]
        env.process(container_process(env, yard, container))
    
    # Run the simulation.
    env.run()