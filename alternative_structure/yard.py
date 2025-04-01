# yard.py

import random
random.seed(42)

import simpy
from container import Container

class Yard:
    """
    Represents a yard for storing containers of a specific category.
    
    Attributes:
        env (simpy.Environment): The simulation environment.
        capacity (int): Maximum number of containers in the yard.
        max_stack_height (int): Maximum stacking height.
        retrieval_delay_per_move (float): Delay (in hours) per level movement when retrieving a container.
        containers (list): List of stored containers.
    """
    def __init__(self, env, capacity, max_stack_height, retrieval_delay_per_move=0.1, initial_container_count=0):
        self.env = env
        self.capacity = capacity
        self.max_stack_height = max_stack_height
        self.retrieval_delay_per_move = retrieval_delay_per_move
        self.containers = []  # List of containers in FIFO order
        
        # Calculate how many containers per stacking level.
        self.per_level = self.capacity // self.max_stack_height
        
        # Pre-populate with initial containers.
        for i in range(initial_container_count):
            container = Container(container_id=i, storage_duration=0, is_initial=True)
            # Set default checkpoints for initial containers.
            container.checkpoints["unload_finish"] = self.env.now
            container.checkpoints["berth_allocation"] = self.env.now
            # Optionally, you might also record a yard arrival checkpoint:
            container.checkpoints["yard_arrival"] = self.env.now
            self.add_container(container)

    def add_container(self, container):
        """
        Add a container to the yard and assign a stacking level.
        Raises an exception if the yard is full.
        """
        if len(self.containers) >= self.capacity:
            raise Exception("Yard is full. Cannot add more containers.")
        container.stacking_level = len(self.containers) // self.per_level
        self.containers.append(container)
        #print(f"Time {self.env.now}: Added {container}")

    def get_occupancy(self):
        """
        Return the current number of containers in the yard.
        """
        return len(self.containers)
    
    def retrieve_ready_container(self):
        """
        Retrieve the container that is ready to depart.
        A container is ready if current time ≥ (arrival_time + storage_duration).
        Among ready containers, the one with the earliest completion time is selected.
        A retrieval delay based on stacking level is then applied.
        Yields:
            simpy.timeout for any wait and the retrieval delay.
        Returns:
            The retrieved container.
        """
        while True:
            ready_containers = [c for c in self.containers if self.env.now >= (c.arrival_time + c.storage_duration)]
            if ready_containers:
                container = min(ready_containers, key=lambda c: c.arrival_time + c.storage_duration)
                self.containers.remove(container)
                retrieval_delay = (self.max_stack_height - 1 - container.stacking_level) * self.retrieval_delay_per_move
                yield self.env.timeout(retrieval_delay)
                return container
            else:
                if self.containers:
                    next_ready_time = min(c.arrival_time + c.storage_duration for c in self.containers)
                    wait_time = next_ready_time - self.env.now
                    yield self.env.timeout(wait_time)
                else:
                    return None


# Testing the updated Yard module with pre-existing containers.
#if __name__ == '__main__':
#    # Set seed for reproducibility.
#    random.seed(42)
#    
#    # Create a SimPy simulation environment.
#    env = simpy.Environment()
#    
#    # Configuration parameters for the yard.
#    capacity = 40
#    max_stack_height = 4    # For instance, 4 levels (i.e., 10 containers per level if capacity=40).
#    retrieval_delay_per_move = 10/60  # hours per level move.
#    initial_container_count = 10    # Number of containers pre-existing in the yard.
#    
#    # Initialize the yard with pre-existing containers.
#    yard = Yard(env, capacity, max_stack_height, retrieval_delay_per_move, initial_container_count)
#    
#    # Add containers arriving via vessels with random storage times.
#    num_arriving = 5
#    storage_mean = 5
#    storage_stdev = 1
#    starting_id = initial_container_count  # Continue container IDs after the pre-existing ones.
#    for i in range(starting_id, starting_id + num_arriving):
#        storage_duration = max(0, random.normalvariate(storage_mean, storage_stdev))
#        container = Container(container_id=i, arrival_time=env.now, storage_duration=storage_duration)
#        yard.add_container(container)
#    
#    def retrieval_process(env, yard):
#        while yard.get_occupancy() > 0:
#            container = yield env.process(yard.retrieve_ready_container())
#            if container is not None:
#                status = "Initial" if container.is_initial else "Arrived"
#                print(f"Time {env.now:.2f}: Retrieved container {container.container_id} ({status})")
#    
#    # Start the retrieval process.
#    env.process(retrieval_process(env, yard))
#    env.run()