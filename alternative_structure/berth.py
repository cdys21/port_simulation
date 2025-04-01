import simpy

class Berth:
    """
    Represents a single berth in the port.
    
    Attributes:
        berth_id (int): Unique identifier for the berth.
        total_cranes (int): Total number of cranes assigned to the berth.
        effective_cranes (int): Number of operational cranes (total_cranes * effective_crane_availability).
    """
    def __init__(self, berth_id, cranes_per_berth, effective_crane_availability):
        self.berth_id = berth_id
        self.total_cranes = cranes_per_berth
        # Calculate effective cranes (rounding down to the nearest integer)
        self.effective_cranes = int(cranes_per_berth * effective_crane_availability)
    
    def __str__(self):
        return f"Berth {self.berth_id} (Cranes: {self.effective_cranes}/{self.total_cranes})"


class BerthManager:
    """
    Manages the pool of berth resources.
    
    Attributes:
        env (simpy.Environment): The simulation environment.
        available_berths (simpy.Store): A store containing available berth objects.
    """
    def __init__(self, env, num_berths, cranes_per_berth, effective_crane_availability):
        self.env = env
        self.available_berths = simpy.Store(env, capacity=num_berths)
        # Populate the store with Berth objects.
        for i in range(num_berths):
            berth = Berth(i, cranes_per_berth, effective_crane_availability)
            self.available_berths.put(berth)
    
    def request_berth(self):
        """
        Request an available berth.
        Returns:
            A berth object when one is available.
        """
        return self.available_berths.get()
    
    def release_berth(self, berth):
        """
        Release a berth back into the pool.
        """
        return self.available_berths.put(berth)


# Test the BerthManager module.
if __name__ == '__main__':
    import random
    random.seed(42)
    
    # Create a SimPy environment.
    env = simpy.Environment()
    
    # Define parameters (using default values as per our configuration).
    num_berths = 4
    cranes_per_berth = 4
    effective_crane_availability = 1.0  # 100% availability.
    
    # Initialize the BerthManager.
    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
    
    def vessel_process(env, berth_manager, vessel_name):
        #print(f"Time {env.now}: {vessel_name} requesting berth")
        # Request a berth.
        berth = yield berth_manager.request_berth()
        #print(f"Time {env.now}: {vessel_name} allocated {berth}")
        # Simulate occupying the berth for 5 time units.
        yield env.timeout(5)
        #print(f"Time {env.now}: {vessel_name} releasing {berth}")
        # Release the berth back to the pool.
        yield berth_manager.release_berth(berth)
    
    # Start two vessel processes to test berth allocation.
    env.process(vessel_process(env, berth_manager, "Vessel A"))
    env.process(vessel_process(env, berth_manager, "Vessel B"))
    
    # Run the simulation.
    env.run()

#if __name__ == '__main__':
#    import random
#    random.seed(42)
#    
#    # Create a SimPy environment.
#    env = simpy.Environment()
#    
#    # Define parameters (using default values as per our configuration).
#    num_berths = 4
#    cranes_per_berth = 4
#    effective_crane_availability = 1.0  # 100% availability.
#    
#    # Initialize the BerthManager.
#    berth_manager = BerthManager(env, num_berths, cranes_per_berth, effective_crane_availability)
#    
#    def vessel_process(env, berth_manager, vessel_name):
#        print(f"Time {env.now}: {vessel_name} requesting berth")
#        # Request a berth.
#        berth = yield berth_manager.request_berth()
#        print(f"Time {env.now}: {vessel_name} allocated {berth}")
#        # Simulate occupying the berth for 5 time units.
#        yield env.timeout(5)
#        print(f"Time {env.now}: {vessel_name} releasing {berth}")
#        # Release the berth back to the pool.
#        yield berth_manager.release_berth(berth)
#    
#    # Start two vessel processes to test berth allocation.
#    env.process(vessel_process(env, berth_manager, "Vessel A"))
#    env.process(vessel_process(env, berth_manager, "Vessel B"))
#    
#    # Run the simulation.
#    env.run()