# metrics.py

class Metrics:
    def __init__(self):
        self.vessel_arrivals = []  # (vessel_name, scheduled_arrival, actual_arrival)
        self.ship_waiting_times = []  # float values (hours)
        self.berth_waiting_times = []  # float values (hours)
        self.unloading_durations = []  # float values (hours)
        self.yard_storage_times = []  # float values (hours)
        self.stacking_retrieval_times = []  # float values (hours)
        self.inland_transport_wait_times = []  # float values (hours)
        self.yard_occupancy = []  # (time, occupancy)
        self.container_departures = []  # (container_id, mode, departure_time, dwell_time)
        self.truck_queue_lengths = []  # (time, length)
        self.train_queue_lengths = []  # (time, length)

    def record_vessel_arrival(self, vessel_name, scheduled, actual):
        self.vessel_arrivals.append((vessel_name, scheduled, actual))

    def record_ship_waiting(self, value):
        self.ship_waiting_times.append(value)

    def record_berth_wait(self, value):
        self.berth_waiting_times.append(value)

    def record_unloading_duration(self, vessel_name, duration):
        self.unloading_durations.append(duration)

    def record_yard_storage(self, value):
        self.yard_storage_times.append(value)

    def record_stacking_retrieval(self, value):
        self.stacking_retrieval_times.append(value)

    def record_inland_transport_wait(self, value):
        self.inland_transport_wait_times.append(value)

    def record_yard_occupancy(self, time, occupancy):
        self.yard_occupancy.append((time, occupancy))

    def record_container_departure(self, container_id, mode, departure_time, dwell_time):
        self.container_departures.append((container_id, mode, departure_time, dwell_time))

    def record_truck_queue(self, time, length):
        self.truck_queue_lengths.append((time, length))

    def record_train_queue(self, time, length):
        self.train_queue_lengths.append((time, length))