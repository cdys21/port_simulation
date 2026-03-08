# metrics.py

class Metrics:
    def __init__(self):
        # List of dictionaries; each dictionary represents one container's final record.
        self.container_records = []
        # List of tuples: (time, yard_identifier, occupancy)
        self.yard_utilization = []
        # List of tuples: (time, truck_queue_length)
        self.truck_queue_lengths = []
        # List of tuples: (time, train_queue_length)
        self.train_queue_lengths = []

    def record_container_departure(self, container):
        """
        Record the final state of a container and calculate derived durations.
        
        The container object should have the following checkpoints:
            - vessel: the vessel that delivered the container.
            - vessel_scheduled_arrival: when the vessel was scheduled to arrive.
            - vessel_arrives: when the vessel actually arrived.
            - vessel_berths: when the vessel berths.
            - entered_yard: when the container enters the yard.
            - retrieval_ready: when the container is ready for retrieval.
            - waiting_for_inland_tsp: when retrieval is complete (container waiting for inland transport).
            - loaded_for_transport: when the container is loaded onto its transport.
            - departed_port: when the container departs the port.
        
        Derived durations:
            - vessel_delays = vessel_arrives - vessel_scheduled_arrival
            - berth_delays = vessel_berths - vessel_arrives
            - unloading_time = entered_yard - vessel_arrives
            - yard_time = retrieval_ready - entered_yard
            - retrieval_time = waiting_for_inland_tsp - retrieval_ready
            - queuing_for_tsp = loaded_for_transport - waiting_for_inland_tsp
            - loading_time = departed_port - loaded_for_transport
        """
        cp = container.checkpoints

        def calc_duration(start_key, end_key):
            if (start_key in cp and end_key in cp and 
                cp[start_key] is not None and cp[end_key] is not None):
                return cp[end_key] - cp[start_key]
            return None

        record = {
            "container_id": container.container_id,
            "is_initial": container.is_initial,
            "mode": container.mode,
            "vessel": cp.get("vessel", None),
            "vessel_scheduled_arrival": cp.get("vessel_scheduled_arrival", None),
            "vessel_arrives": cp.get("vessel_arrives", None),
            "vessel_berths": cp.get("vessel_berths", None),
            "entered_yard": cp.get("entered_yard", None),
            "retrieval_ready": cp.get("retrieval_ready", None),
            "waiting_for_inland_tsp": cp.get("waiting_for_inland_tsp", None),
            "loaded_for_transport": cp.get("loaded_for_transport", None),
            "departed_port": cp.get("departed_port", None),
            "vessel_delays": calc_duration("vessel_scheduled_arrival", "vessel_arrives"),
            "berth_delays": calc_duration("vessel_arrives", "vessel_berths"),
            "unloading_time": calc_duration("vessel_arrives", "entered_yard"),
            "yard_time": calc_duration("entered_yard", "retrieval_ready"),
            "retrieval_time": calc_duration("retrieval_ready", "waiting_for_inland_tsp"),
            "queuing_for_tsp": calc_duration("waiting_for_inland_tsp", "loaded_for_transport"),
            "loading_time": calc_duration("loaded_for_transport", "departed_port"),
            "total_dwell_time": calc_duration("vessel_arrives", "departed_port")
        }
        self.container_records.append(record)

    def record_yard_utilization(self, time, yard_identifier, occupancy):
        """
        Record yard occupancy at a given time.
        
        Args:
            time (float): Simulation time.
            yard_identifier (str): Identifier or category for the yard.
            occupancy (int): Number of containers in the yard at that time.
        """
        self.yard_utilization.append((time, yard_identifier, occupancy))

    def record_truck_queue(self, time, length):
        """
        Record the length of the truck queue at a given time.
        
        Args:
            time (float): Simulation time.
            length (int): Length of the truck queue.
        """
        self.truck_queue_lengths.append((time, length))

    def record_train_queue(self, time, length):
        """
        Record the length of the train queue at a given time.
        
        Args:
            time (float): Simulation time.
            length (int): Length of the train queue.
        """
        self.train_queue_lengths.append((time, length))
