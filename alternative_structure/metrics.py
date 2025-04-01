# metrics.py

class Metrics:
    def __init__(self):
        # Records vessel arrivals as tuples: (vessel name, scheduled arrival, actual arrival)
        self.vessel_arrivals = []  
        # Records berth waiting times as tuples: (vessel name, waiting time)
        self.berth_waiting_times = []  
        # Records unloading durations as tuples: (vessel name, unloading duration)
        self.unloading_durations = []  
        # Records yard occupancy snapshots as tuples: (simulation time, occupancy)
        self.yard_occupancy = []  
        # Records container departures as tuples: (container id, departure mode, departure time)
        self.container_departures = []  

    def record_vessel_arrival(self, name, scheduled, actual):
        self.vessel_arrivals.append((name, scheduled, actual))

    def record_berth_wait(self, name, wait_time):
        self.berth_waiting_times.append((name, wait_time))

    def record_unloading(self, name, duration):
        self.unloading_durations.append((name, duration))

    def record_yard_occupancy(self, time, occupancy):
        self.yard_occupancy.append((time, occupancy))

    def record_container_departure(self, container_id, mode, departure_time):
        self.container_departures.append((container_id, mode, departure_time))

    def summary(self):
        print("\n----- Metrics Summary -----")
        print("Vessel Arrivals (Name, Scheduled, Actual):")
        for rec in self.vessel_arrivals:
            print("  ", rec)
        print("Berth Waiting Times (Vessel, Wait Time):")
        for rec in self.berth_waiting_times:
            print("  ", rec)
        print("Unloading Durations (Vessel, Duration):")
        for rec in self.unloading_durations:
            print("  ", rec)
        print("Yard Occupancy (Time, Occupancy):")
        for rec in self.yard_occupancy:
            print("  ", rec)
        print("Container Departures (Container ID, Mode, Departure Time):")
        for rec in self.container_departures:
            print("  ", rec)
        print("---------------------------\n")