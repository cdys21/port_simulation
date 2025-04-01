# metrics.py

class Metrics:
    def __init__(self):
        # Records vessel arrivals as tuples: (vessel_name, scheduled_arrival, actual_arrival)
        self.vessel_arrivals = []
        # Records berth waiting times as tuples: (vessel_name, wait_time)
        self.berth_waiting_times = []
        # Records unloading durations as tuples: (vessel_name, unload_duration)
        self.unloading_durations = []
        # Records yard occupancy snapshots as tuples: (simulation_time, occupancy)
        self.yard_occupancy = []
        # Records container departures as tuples: (container_id, departure_mode, departure_time)
        self.container_departures = []

    def record_vessel_arrival(self, vessel_name, scheduled, actual):
        self.vessel_arrivals.append((vessel_name, scheduled, actual))

    def record_berth_wait(self, vessel_name, wait_time):
        self.berth_waiting_times.append((vessel_name, wait_time))

    def record_unloading_duration(self, vessel_name, duration):
        self.unloading_durations.append((vessel_name, duration))

    def record_yard_occupancy(self, time, occupancy):
        self.yard_occupancy.append((time, occupancy))

    def record_container_departure(self, container_id, mode, departure_time):
        self.container_departures.append((container_id, mode, departure_time))

    def summary(self):
        print("\n----- Simulation Metrics Summary -----")
        print("Vessel Arrivals:")
        for vessel, scheduled, actual in self.vessel_arrivals:
            print(f"  Vessel {vessel}: scheduled {scheduled:.2f}h, actual {actual:.2f}h")
        print("Berth Waiting Times:")
        for vessel, wait_time in self.berth_waiting_times:
            print(f"  Vessel {vessel} waited {wait_time:.2f}h")
        print("Unloading Durations:")
        for vessel, duration in self.unloading_durations:
            print(f"  Vessel {vessel} unloaded in {duration:.2f}h")
        print("Yard Occupancy Snapshots:")
        for t, occ in self.yard_occupancy:
            print(f"  Time {t:.2f}h: occupancy {occ}")
        print("Container Departures:")
        for cid, mode, t in self.container_departures:
            print(f"  Container {cid} departed by {mode} at {t:.2f}h")
        print("---------------------------------------\n")