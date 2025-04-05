# config.py
default_config = {
    "berth_count": 4,
    "gate_count": 120,
    "simulation_duration": 150,
    "save_csv": False,
    "output_file": "container_checkpoints.csv",
    "container_types": [
        {
            "name": "Standard",
            "yard_capacity": 30000,
            "initial_yard_fill": 0.6,
            "rail_percentage": 0.15,
            "unload_time": [0.01, 0.033, 0.02],
            "truck_process_time": [0.1, 0.3, 0.13]
        },
        {
            "name": "Reefer",
            "yard_capacity": 10000,
            "initial_yard_fill": 0.5,
            "rail_percentage": 0.20,
            "unload_time": [0.02, 0.04, 0.03],
            "truck_process_time": [0.15, 0.35, 0.2]
        },
        {
            "name": "Hazardous",
            "yard_capacity": 5000,
            "initial_yard_fill": 0.4,
            "rail_percentage": 0.05,
            "unload_time": [0.015, 0.05, 0.03],
            "truck_process_time": [0.2, 0.4, 0.3]
        }
    ],
    "vessels": [
        {
            "name": "CEZANNE",
            "container_counts": {"Standard": 10000, "Reefer": 0, "Hazardous": 0},
            "day": 1,
            "hour": 8
        },
        {
            "name": "CCNI ANDES",
            "container_counts": {"Standard": 0, "Reefer": 700, "Hazardous": 500},
            "day": 1,
            "hour": 10
        },
        {
            "name": "CMA CGM LEO",
            "container_counts": {"Standard": 1300, "Reefer": 600, "Hazardous": 287},
            "day": 1,
            "hour": 14
        },
        {
            "name": "ONE REINFORCEMENT",
            "container_counts": {"Standard": 500, "Reefer": 5000, "Hazardous": 0},
            "day": 1,
            "hour": 15
        },
        {
            "name": "POLAR ECUADOR",
            "container_counts": {"Standard": 900, "Reefer": 450, "Hazardous": 81},
            "day": 1,
            "hour": 16
        },
        {
            "name": "W KITHIRA",
            "container_counts": {"Standard": 0, "Reefer": 300, "Hazardous": 98},
            "day": 2,
            "hour": 8
        },
        {
            "name": "MAERSK ATHABASCA",
            "container_counts": {"Standard": 600, "Reefer": 0, "Hazardous": 96},
            "day": 2,
            "hour": 8
        },
        {
            "name": "MAERSK SENTOSA",
            "container_counts": {"Standard": 500, "Reefer": 250, "Hazardous": 0},
            "day": 2,
            "hour": 12
        },
        {
            "name": "SUAPE EXPRESS",
            "container_counts": {"Standard": 600, "Reefer": 0, "Hazardous": 5000},
            "day": 2,
            "hour": 15
        }
    ]
}
