# rules.py
import random
import math

def determine_stacking_level(yard_level, yard_capacity, max_stacking_height):
    """
    Determine stacking level based on current yard utilization.
    """
    utilization = yard_level / yard_capacity if yard_capacity > 0 else 0
    if max_stacking_height == 1:
        return 1
    avg_stack_height = utilization * max_stacking_height
    if avg_stack_height < 1:
        return 1
    current_filling = min(int(avg_stack_height) + 1, max_stacking_height)
    return current_filling

def calculate_stacking_retrieval_time(stacking_level, max_stacking_height, base_time, retrieval_factor, yard_utilization):
    """
    Calculate additional retrieval time based on stacking level.
    """
    containers_to_move = max(0, max_stacking_height - stacking_level)
    additional_time = containers_to_move * retrieval_factor
    congestion_factor = 1.0
    if yard_utilization > 0.5:
        congestion_factor = 1.0 + ((yard_utilization - 0.5) / 0.5) ** 2 * 2.0
    return (base_time + additional_time) * congestion_factor

def calculate_actual_arrival(expected_arrival, std_dev):
    """
    Calculate actual arrival time (in minutes) given an expected arrival and variability.
    """
    random_factor = random.normalvariate(1.0, std_dev)
    time_delta = (random_factor - 1.0) * 60  # convert hours to minutes
    return max(0, expected_arrival + time_delta)