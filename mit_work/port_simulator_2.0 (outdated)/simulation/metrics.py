# simulation/metrics.py
import pandas as pd

def create_dataframe(all_containers):
    """Generate a DataFrame from container objects."""
    data = []
    for i, container in enumerate(all_containers):
        data.append({
            'container_id': f'C{i+1}',
            'vessel': container.vessel,
            'mode': container.mode,
            'vessel_scheduled_arrival': container.vessel_scheduled_arrival,
            'vessel_arrives': container.vessel_arrives,
            'vessel_berths': container.vessel_berths,
            'entered_yard': container.entered_yard,
            'waiting_for_inland_tsp': container.waiting_for_inland_tsp,
            'loaded_for_transport': container.loaded_for_transport,
            'departed_port': container.departed_port
        })
    df = pd.DataFrame(data)
    return df
