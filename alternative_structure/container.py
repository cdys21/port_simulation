class Container:
    """
    Represents a container stored in the yard.
    
    Attributes:
        container_id (int): Unique identifier.
        category (str): Container category.
        storage_duration (float): Planned waiting period in the yard.
        is_initial (bool): True if pre-existing.
        mode (str): Departure mode ("Rail" or "Road").
        checkpoints (dict): Dictionary for storing key event timestamps.
    """
    def __init__(self, container_id, category="ANY", storage_duration=0.0, is_initial=False):
        self.container_id = container_id
        self.category = category
        self.storage_duration = storage_duration
        self.is_initial = is_initial
        self.mode = None
        self.checkpoints = {}  # Initialize empty dictionary for timestamps

    def __str__(self):
        init_str = "Initial" if self.is_initial else "Arrived"
        return (f"Container(id={self.container_id}, category={self.category}, "
                f"{init_str}, storage_duration={self.storage_duration:.2f}, "
                f"mode={self.mode}, checkpoints={self.checkpoints})")