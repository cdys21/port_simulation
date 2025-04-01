# vessel.py

import random
random.seed(42)

class Vessel:
    """
    Represents a vessel in the simulation.
    
    Attributes:
        name (str): Name of the vessel.
        container_count (int): Number of containers on the vessel.
        expected_arrival_day (int): Day of scheduled arrival (starting at 1).
        expected_arrival (float): Hour of scheduled arrival (24-hour clock).
        arrival_variability (dict): Triangular distribution parameters with keys 'min', 'mode', 'max' (in hours).
        scheduled_arrival (float): Computed arrival time (in hours since simulation start).
        actual_arrival (float): Adjusted arrival time after applying variability (vessel_arrives).
    """
    def __init__(self, name, container_count, expected_arrival_day, expected_arrival, arrival_variability):
        self.name = name
        self.container_count = container_count
        self.expected_arrival_day = expected_arrival_day
        self.expected_arrival = expected_arrival
        self.arrival_variability = arrival_variability
        
        # Calculate scheduled arrival as hours since simulation start.
        self.scheduled_arrival = self.compute_scheduled_arrival()
        self.actual_arrival = None  # This will serve as vessel_arrives

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
        Sets self.actual_arrival (vessel_arrives).
        
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
                    f"scheduled_arrival={self.scheduled_arrival:.2f}, vessel_arrives={self.actual_arrival:.2f})")
        else:
            return (f"Vessel(name={self.name}, containers={self.container_count}, "
                    f"scheduled_arrival={self.scheduled_arrival:.2f}, vessel_arrives=Not set)")
