port_simulation/
│
├── config/
│   └── config.json          # Simulation parameters
│
├── src/
│   ├── managers/
│   │   ├── yard_manager.py  # Yard management logic
│   │   ├── vessel_manager.py # Vessel handling logic
│   │   ├── road_transport.py # Road transport logic
│   │   ├── rail_transport.py # Rail transport logic
│   │   └── monitor.py       # Monitoring and logging
│   ├── models/
│   │   └── container.py     # Container data structure
│   ├── utils/
│   │   └── helpers.py       # Shared utility functions
│   ├── simulation.py        # Core simulation logic
│   └── factory.py           # Manager creation logic
│
├── tests/
│   └── test_simulation.py   # Unit tests
│
├── main.py                  # Program entry point
└── requirements.txt         # Dependencies