# vessel.py

import random

class Vessel:
    """
    Represents a vessel in the simulation.
    
    Attributes:
        name (str): Name of the vessel.
        container_count (int): Number of containers on the vessel.
        expected_arrival_day (int): Day (starting at 1) when the vessel is scheduled to arrive.
        expected_arrival (float): Hour of the day when the vessel is scheduled to arrive.
        arrival_variability (dict): Triangular distribution parameters with keys 'min', 'mode', 'max' (in hours).
        scheduled_arrival (float): Computed arrival time (in hours since simulation start).
        actual_arrival (float): Adjusted arrival time after applying variability.
    """
    def __init__(self, name, container_count, expected_arrival_day, expected_arrival, arrival_variability):
        self.name = name
        self.container_count = container_count
        self.expected_arrival_day = expected_arrival_day
        self.expected_arrival = expected_arrival
        self.arrival_variability = arrival_variability
        
        # Calculate scheduled arrival as hours since simulation start (assuming day 1, hour 0)
        self.scheduled_arrival = self.compute_scheduled_arrival()
        self.actual_arrival = None

    def compute_scheduled_arrival(self):
        """
        Compute the scheduled arrival time in hours.
        For example, if expected_arrival_day = 1 and expected_arrival = 8, 
        the scheduled arrival is 8 hours since simulation start.
        """
        return (self.expected_arrival_day - 1) * 24 + self.expected_arrival

    def adjust_arrival(self):
        """
        Adjust the scheduled arrival using a triangular distribution to simulate variability.
        Returns:
            float: The actual arrival time in hours.
        """
        delta = random.triangular(
            self.arrival_variability['min'],
            self.arrival_variability['max'],
            self.arrival_variability['mode']
        )
        self.actual_arrival = self.scheduled_arrival + delta
        return self.actual_arrival

    def __str__(self):
        if self.actual_arrival is not None:
            return (f"Vessel(name={self.name}, containers={self.container_count}, "
                    f"scheduled_arrival={self.scheduled_arrival:.2f}, actual_arrival={self.actual_arrival:.2f})")
        else:
            return (f"Vessel(name={self.name}, containers={self.container_count}, "
                    f"scheduled_arrival={self.scheduled_arrival:.2f}, actual_arrival=Not set)")

#if __name__ == '__main__':
#    # Set seed for reproducibility
#    random.seed(42)
#    
#    # Default triangular distribution parameters for arrival variability: min=-1, mode=2, max=5
#    arrival_variability = {'min': -1, 'mode': 2, 'max': 5}
#    
#    # Create a sample vessel, for example, "CEZANNE" arriving on day 1 at 8 AM with 2642 containers.
#    vessel = Vessel(name="CEZANNE", container_count=2642, expected_arrival_day=1, expected_arrival=8, arrival_variability=arrival_variability)
#    
#    # Output scheduled arrival time (in hours since simulation start)
#    print("Scheduled arrival (in hours):", vessel.scheduled_arrival)
#    
#    # Adjust and output actual arrival time
#    actual_arrival = vessel.adjust_arrival()
#    print("Actual arrival (in hours):", actual_arrival)
#    
#    # Print the vessel's details
#    print(vessel)