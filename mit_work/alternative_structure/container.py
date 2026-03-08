class Container:
    """
    Represents a container in the simulation.
    
    Checkpoints:
        - vessel: the vessel that delivered the container.
        - vessel_scheduled_arrival: when the vessel was scheduled to arrive.
        - vessel_arrives: when the vessel actually arrived.
        - vessel_berths: when the vessel berths.
        - entered_yard: when the container enters the yard.
        - retrieval_ready: when the container is ready for retrieval.
        - waiting_for_inland_tsp: when retrieval is complete (container waiting for inland transport).
        - loaded_for_transport: when the container is loaded onto its transport.
        - departed_port: when the container departs the port.
    """
    def __init__(self, container_id, category="ANY", is_initial=False):
        self.container_id = container_id
        self.category = category
        self.is_initial = is_initial
        self.mode = None
        self.checkpoints = {}  # Expected keys: 'vessel', 'vessel_scheduled_arrival', 'vessel_arrives', 'vessel_berths', 'entered_yard', 'retrieval_ready', 'waiting_for_inland_tsp', 'loaded_for_transport', 'departed_port'

    def __str__(self):
        init_status = "Initial" if self.is_initial else "Arrived"
        return (f"Container(id={self.container_id}, category={self.category}, {init_status}, "
                f"mode={self.mode}, checkpoints={self.checkpoints})")
