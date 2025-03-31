# ______________________________________________________________________________________
# stats.py
import numpy as np
from collections import defaultdict
from datetime import timedelta

class Statistics:
    def __init__(self, env, sim_start_time=None):
        self.env = env
        self.sim_start_time = sim_start_time

        self.containers = {
            'total': 0,
            'dry': {'truck': 0, 'train': 0},
            'reefer': {'truck': 0, 'train': 0}
        }
        self.arrivals = {
            'ships': 0,
            'containers': {'total': 0, 'dry': 0, 'reefer': 0}
        }
        self.departures = {
            'truck': {'total': 0, 'by_hour': [0]*24, 'dry': 0, 'reefer': 0},
            'train': {'total': 0, 'by_hour': [0]*24, 'dry': 0, 'reefer': 0}
        }
        self.yard_state = {'current': {'dry': 0, 'reefer': 0}, 'max': {'dry': 0, 'reefer': 0}}
        self.yard_full_events = 0

        self.yard_waiting_times = {'dry': [], 'reefer': []}
        self.dwell_times = {'dry': [], 'reefer': []}
        self.wait_times = {'ship': [], 'gate': [], 'train': [], 'berth': [], 'crane': []}
        self.missed_train_connections = 0

        self.hourly_stats = {
            'arrivals': defaultdict(lambda: defaultdict(int)),
            'departures': {
                'truck': defaultdict(lambda: defaultdict(int)),
                'train': defaultdict(lambda: defaultdict(int))
            }
        }
        self.yard_utilization = {
            'dry': {'truck': defaultdict(int), 'train': defaultdict(int)},
            'reefer': {'truck': defaultdict(int), 'train': defaultdict(int)}
        }
        self.resource_usage_by_hour = {
            'berths': defaultdict(float),
            'cranes': defaultdict(float),
            'gate': defaultdict(float),
            'yard': defaultdict(float)
        }

        self.resource_usage_by_minute = {
            'berths': defaultdict(float),
            'cranes': defaultdict(float),
            'gate': defaultdict(float),
            'yard': defaultdict(float)
        }
        self.train_departure_records = []

        # Dwell time components in minutes
        self.dwell_components = {
            'ship_arrival_delay': [],
            'berth_wait_time': [],
            'container_unloading': [],
            'yard_storage': [],
            'departure_wait': [],
            'stacking_retrieval': []
        }
        # Tracking stacking levels
        self.stacking_levels = {level: 0 for level in range(1, 7)}
        
        # Flag to control dwell time tracking.
        # When set to False, no further dwell-time data will be recorded.
        self.dwell_tracking_active = True

        self.truck_waiting_over_time = []
        self.train_waiting_over_time = []

        self.gate_departures_by_hour = defaultdict(int)

    def log_train_waiting(self, current_time, train_waiting):
        self.train_waiting_over_time.append({
            "time": current_time,  # simulation time in minutes
            "train_waiting": train_waiting
        })

    def log_truck_waiting(self, current_time, truck_waiting):
        self.truck_waiting_over_time.append({
            "time": current_time,  # simulation time in minutes
            "truck_waiting": truck_waiting
        })

    def log_ship_arrival(self):
        self.arrivals['ships'] += 1

    def log_container_arrival(self, container_type):
        self.arrivals['containers']['total'] += 1
        self.arrivals['containers'][container_type] += 1
        current_hour = int(self.env.now / 60)
        self.hourly_stats['arrivals'][current_hour][container_type] += 1

    def log_container_departure(self, container_type, modal, hour):
        self.departures[modal]['total'] += 1
        self.departures[modal]['by_hour'][hour] += 1
        self.departures[modal][container_type] += 1
        current_hour = int(self.env.now / 60)
        self.hourly_stats['departures'][modal][current_hour][container_type] += 1

    def update_yard_state(self, dry_truck, dry_train, reefer_truck, reefer_train):
        total_dry = dry_truck + dry_train
        total_reefer = reefer_truck + reefer_train
        self.yard_state['current']['dry'] = total_dry
        self.yard_state['current']['reefer'] = total_reefer
        self.yard_state['max']['dry'] = max(self.yard_state['max']['dry'], total_dry)
        self.yard_state['max']['reefer'] = max(self.yard_state['max']['reefer'], total_reefer)
        current_minute = int(self.env.now)
        # Store counts separately for later granular analysis if needed.
        self.yard_utilization['dry']['truck'][current_minute] = dry_truck
        self.yard_utilization['dry']['train'][current_minute] = dry_train
        self.yard_utilization['reefer']['truck'][current_minute] = reefer_truck
        self.yard_utilization['reefer']['train'][current_minute] = reefer_train


    
    def log_container(self, container_type, modal):
        self.containers['total'] += 1
        self.containers[container_type][modal] += 1

    def log_wait_time(self, wait_type, wait_time):
        self.wait_times[wait_type].append(wait_time)

    def log_yard_full(self):
        self.yard_full_events += 1

    def log_missed_train(self):
        self.missed_train_connections += 1

    def log_train_departure(self, dry_loaded, reefer_loaded, capacity, backlog):
        total_loaded = dry_loaded + reefer_loaded
        fullness_percentage = (total_loaded / capacity) * 100 if capacity > 0 else 0
        if self.sim_start_time:
            departure_dt = self.sim_start_time + timedelta(minutes=self.env.now)
        else:
            departure_dt = self.env.now
        # Log only the simplified departure information.
        self.train_departure_records.append({
            "Departure Time": departure_dt,
            "Dry Loaded": dry_loaded,
            "Reefer Loaded": reefer_loaded,
            "Total Loaded": total_loaded,
            "Capacity": capacity,
            "Fullness Percentage": fullness_percentage,
            "Backlog": backlog
        })

    def log_dwell_components(self, ship_arrival_delay=None, berth_wait_time=None,
                             container_unloading=None, yard_storage=None, departure_wait=None):
        # Only log if dwell tracking is active.
        if not self.dwell_tracking_active:
            return
        if ship_arrival_delay is not None:
            self.dwell_components['ship_arrival_delay'].append(ship_arrival_delay)
        if berth_wait_time is not None:
            self.dwell_components['berth_wait_time'].append(berth_wait_time)
        if container_unloading is not None:
            self.dwell_components['container_unloading'].append(container_unloading)
        if yard_storage is not None:
            self.dwell_components['yard_storage'].append(yard_storage)
        if departure_wait is not None:
            self.dwell_components['departure_wait'].append(departure_wait)

    def log_stacking_level(self, level):
        if level in self.stacking_levels:
            self.stacking_levels[level] += 1

    def log_stacking_retrieval_time(self, time):
        if self.dwell_tracking_active:
            self.dwell_components['stacking_retrieval'].append(time)

    def log_dwell_time(self, container_type, time):
        if self.dwell_tracking_active:
            self.dwell_times[container_type].append(time)

    def get_summary(self):
        total = self.containers['total']
        dry_total = self.containers['dry']['truck'] + self.containers['dry']['train']
        reefer_total = self.containers['reefer']['truck'] + self.containers['reefer']['train']
        return {
            'Arrivals': {
                'Ships': self.arrivals['ships'],
                'Containers': {
                    'Total': self.arrivals['containers']['total'],
                    'Dry': self.arrivals['containers']['dry'],
                    'Reefer': self.arrivals['containers']['reefer']
                }
            },
            'Departures': {
                'Truck': {
                    'Total': self.departures['truck']['total'],
                    'Dry': self.departures['truck']['dry'],
                    'Reefer': self.departures['truck']['reefer'],
                    'Peak Hour': (max(enumerate(self.departures['truck']['by_hour']), key=lambda x: x[1])[0]
                                  if any(self.departures['truck']['by_hour']) else 0)
                },
                'Train': {
                    'Total': self.departures['train']['total'],
                    'Dry': self.departures['train']['dry'],
                    'Reefer': self.departures['train']['reefer'],
                    'Peak Hour': (max(enumerate(self.departures['train']['by_hour']), key=lambda x: x[1])[0]
                                  if any(self.departures['train']['by_hour']) else 0)
                }
            },
            'Yard State': {
                'Current': self.yard_state['current'],
                'Maximum': self.yard_state['max']
            },
            'Container Counts': {
                'Total Processed': total,
                'By Type': {
                    'Dry': {
                        'Total': dry_total,
                        'Truck': self.containers['dry']['truck'],
                        'Train': self.containers['dry']['train']
                    },
                    'Reefer': {
                        'Total': reefer_total,
                        'Truck': self.containers['reefer']['truck'],
                        'Train': self.containers['reefer']['train']
                    }
                },
                'Modal Split': {
                    'Truck': ((self.containers['dry']['truck'] + self.containers['reefer']['truck']) / total if total > 0 else 0),
                    'Train': ((self.containers['dry']['train'] + self.containers['reefer']['train']) / total if total > 0 else 0)
                }
            },
            'Dwell Times (days)': {
                'Dry': {
                    'Mean': np.mean(self.dwell_times['dry']) / (24 * 60) if self.dwell_times['dry'] else 0,
                    'Median': np.median(self.dwell_times['dry']) / (24 * 60) if self.dwell_times['dry'] else 0,
                    'Std Dev': np.std(self.dwell_times['dry']) / (24 * 60) if self.dwell_times['dry'] else 0,
                    '95th Percentile': (np.percentile(self.dwell_times['dry'], 95) / (24 * 60) if self.dwell_times['dry'] else 0)
                },
                'Reefer': {
                    'Mean': np.mean(self.dwell_times['reefer']) / (24 * 60) if self.dwell_times['reefer'] else 0,
                    'Median': np.median(self.dwell_times['reefer']) / (24 * 60) if self.dwell_times['reefer'] else 0,
                    'Std Dev': np.std(self.dwell_times['reefer']) / (24 * 60) if self.dwell_times['reefer'] else 0,
                    '95th Percentile': (np.percentile(self.dwell_times['reefer'], 95) / (24 * 60) if self.dwell_times['reefer'] else 0)
                }
            },
            'Wait Times (minutes)': {
                'Ship': self.wait_times['ship'],
                'Berth': self.wait_times['berth'],
                'Crane': self.wait_times['crane'],
                'Gate': self.wait_times['gate'],
                'Train': self.wait_times['train']
            },
            'Operational Issues': {
                'Yard Full Events': self.yard_full_events,
                'Missed Train Connections': self.missed_train_connections
            }
        }