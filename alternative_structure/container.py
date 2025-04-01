#container.py

class Container:
    """
    Represents a container in the simulation.
    
    Checkpoints (to be set by simulation processes):
        - 'vessel': Name or identifier of the vessel that delivered the container.
        - 'yard_entry': Timestamp when the container enters the yard.
        - 'yard_exit': Timestamp when the container ends its storage time in the yard.
        - 'inland_loading': Timestamp when the container is loaded into inland transport,
                            after accounting for any stacking delays.
        - 'departure': Timestamp when the container leaves the port, considering transport queues.
    
    Attributes:
        container_id (int): Unique identifier.
        category (str): Category of the container.
        is_initial (bool): True if the container is pre-existing.
        mode (str): Departure mode ("Rail" or "Road").
        checkpoints (dict): Records timestamps for events as described above.
        stacking_level (int): Stacking level assigned within the yard.
    """
    def __init__(self, container_id, category="ANY", is_initial=False):
        self.container_id = container_id
        self.category = category
        self.is_initial = is_initial
        self.mode = None
        self.checkpoints = {}  # Expected keys: 'vessel', 'yard_entry', 'yard_exit', 'inland_loading', 'departure'
        self.stacking_level = None

    def __str__(self):
        init_status = "Initial" if self.is_initial else "Arrived"
        return (f"Container(id={self.container_id}, category={self.category}, {init_status}, "
                f"mode={self.mode}, stacking_level={self.stacking_level}, checkpoints={self.checkpoints})")
