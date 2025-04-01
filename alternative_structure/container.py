# container.py

class Container:
    """
    Represents a container.
    
    Attributes:
        container_id (int): Unique identifier.
        category (str): Container category.
        arrival_time (float): Time when the container arrives at the yard.
        storage_duration (float): Planned storage time in the yard.
        is_initial (bool): True if the container is pre-existing.
        mode (str): Departure mode ("Rail" or "Road").
        checkpoints (dict): Dictionary to store key event timestamps.
    """
    def __init__(self, container_id, category="ANY", arrival_time=0.0, storage_duration=0.0, is_initial=False):
        self.container_id = container_id
        self.category = category
        self.arrival_time = arrival_time
        self.storage_duration = storage_duration
        self.is_initial = is_initial
        self.mode = None
        self.checkpoints = {}  # To store timestamps for checkpoints

    def __str__(self):
        init_str = "Initial" if self.is_initial else "Arrived"
        return (f"Container(id={self.container_id}, category={self.category}, {init_str}, "
                f"arrival_time={self.arrival_time}, storage_duration={self.storage_duration:.2f}, "
                f"mode={self.mode}, checkpoints={self.checkpoints})")