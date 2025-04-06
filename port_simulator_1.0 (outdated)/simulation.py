# simulation.py
import simpy
import random
import time
import math  # Ensure math is imported
import streamlit as st  # Import Streamlit here for progress bar etc.
from models import Container, Ship
from stats import Statistics
from datetime import timedelta  # add at top if not already imported
from rules import calculate_actual_arrival, calculate_stacking_retrieval_time

class PortSimulation:
    def __init__(
        self,
        max_berths,
        cranes_per_berth,
        unload_time_mean,
        unload_time_std,
        berth_transition_time,
        container_types,
        modal_split,
        gate_hours,
        ship_schedule,
        trains_per_day,
        train_capacity,
        arrival_time_variability,
        starting_yard_util_percent=50,
        simulation_start=None,
        effective_berth_availability=1.0,
        effective_crane_availability=1.0,
        effective_gate_availability=1.0,
        effective_yard_availability=1.0,
        max_stacking_height=4,
        stacking_retrieval_base_time=15,
        stacking_retrieval_factor=10
    ):
        self.env = simpy.Environment()
        self.max_berths = max_berths
        self.cranes_per_berth = cranes_per_berth
        self.unload_time_mean = unload_time_mean
        self.unload_time_std = unload_time_std
        self.berth_transition_time = berth_transition_time
        self.container_types = container_types
        self.modal_split = modal_split
        self.gate_hours = gate_hours
        self.ship_schedule = ship_schedule
        self.trains_per_day = trains_per_day
        self.train_capacity = train_capacity
        self.arrival_time_variability = arrival_time_variability

        self.effective_berth = effective_berth_availability
        self.effective_crane = effective_crane_availability
        self.effective_gate = effective_gate_availability
        self.effective_yard = effective_yard_availability

        self.max_stacking_height = max_stacking_height
        self.stacking_retrieval_base_time = stacking_retrieval_base_time
        self.stacking_retrieval_factor = stacking_retrieval_factor

        self.gate_truck_capacity = self.gate_hours.get("trucks_per_hour", 500)

        self.berths = simpy.Resource(self.env, capacity=self.max_berths)
        self.cranes = simpy.Resource(self.env, capacity=self.max_berths * self.cranes_per_berth)
        self.gate = simpy.Resource(self.env, capacity=self.gate_hours["gates_capacity"])

        # Yard containers and capacities
        self.yard_containers = {
            'dry': {'truck': [], 'train': []},
            'reefer': {'truck': [], 'train': []}
        }
        self.regular_yard = {
            'truck': simpy.Container(self.env, capacity=int(25000 * modal_split["truck"])),
            'train': simpy.Container(self.env, capacity=int(25000 * modal_split["train"]))
        }
        self.reefer_yard = {
            'truck': simpy.Container(self.env, capacity=int(2000 * modal_split["truck"])),
            'train': simpy.Container(self.env, capacity=int(2000 * modal_split["train"]))
        }
        
        fraction = starting_yard_util_percent / 100.0
        self.initial_containers = []  # track initial yard containers
        # Create initial yard containers – mark these as NOT from a vessel.
        for yard, ctype in [(self.regular_yard, 'dry'), (self.reefer_yard, 'reefer')]:
            for modal in yard.keys():
                initial_fill = int(yard[modal].capacity * fraction)
                for i in range(initial_fill):
                    container_id = f"initial_{ctype}_{modal}_{i}"
                    container = Container(
                        id=container_id,
                        arrival_time=self.env.now,
                        container_types=self.container_types,
                        modal_split=self.modal_split
                    )
                    # Force correct type and modal
                    container.type = ctype  
                    container.modal = modal  
                    container.is_new = True  # so dwell time is tracked
                    container.from_vessel = False  # Mark as NOT from vessel
                    
                    self.env.process(self.process_container(container))
                    self.initial_containers.append(container)

        self.total_expected_containers = sum(ship["containers"] for ship in self.ship_schedule) + len(self.initial_containers)

        interval = 24 / self.trains_per_day
        self.train_times = [interval * i for i in range(self.trains_per_day)]
        self.stats = Statistics(self.env, sim_start_time=simulation_start)
        # Flag to control dwell tracking
        self.stats.dwell_tracking_active = True  
        self.ship_arrivals = []
        self.all_containers = []

        self.env.process(self.schedule_trains())
        self.env.process(self.monitor_utilization())

    def schedule_trains(self):
        # Compute departure times for a day based on the number of trains.
        interval = 24 / self.trains_per_day
        self.train_times = [interval * i for i in range(self.trains_per_day)]
        
        while True:
            # Convert the current simulation time (in minutes) to a datetime.
            if self.stats.sim_start_time:
                current_dt = self.stats.sim_start_time + timedelta(minutes=self.env.now)
            else:
                # Assume simulation starts at midnight if no start time is provided.
                current_dt = self.stats.sim_start_time = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(minutes=self.env.now)
            
            # Determine current time in hours (as a float).
            current_hour = current_dt.hour + current_dt.minute / 60.0 + current_dt.second / 3600.0
            
            # Find the next departure hour from the fixed schedule.
            next_train_hour = None
            for t in self.train_times:
                if t > current_hour:
                    next_train_hour = t
                    break
            if next_train_hour is None:
                # If no departure remains today, schedule the first train of the next day.
                next_train_hour = self.train_times[0] + 24
            
            # Calculate the wait time until the next departure (in minutes).
            wait_hours = next_train_hour - current_hour
            wait_minutes = wait_hours * 60
            
            yield self.env.timeout(wait_minutes)
            self.env.process(self.handle_train_departure())

    def monitor_utilization(self):
        while True:
            current_minute = int(self.env.now)  # env.now is in minutes
            absolute_hour = int(self.env.now / 60)  # Total hours since simulation start

            # Berth utilization: instantaneous usage.
            berths_in_use = self.berths.count
            self.stats.resource_usage_by_minute['berths'][current_minute] = (
                berths_in_use / (self.berths.capacity * self.effective_berth)
                if self.berths.capacity > 0 else 0
            )

            # Crane utilization: instantaneous usage.
            cranes_in_use = self.cranes.count
            self.stats.resource_usage_by_minute['cranes'][current_minute] = (
                berths_in_use / (self.berths.capacity * self.effective_berth)
                if self.berths.capacity > 0 else 0
            )

            # Gate utilization: computed using absolute hour
            gate_utilization = self.gate.count / self.gate.capacity if self.gate.capacity > 0 else 0
            self.stats.resource_usage_by_minute['gate'][current_minute] = gate_utilization

            # Yard utilization: aggregated across truck and train for both regular and reefer yards.
            reg_truck = self.regular_yard['truck'].level
            reg_train = self.regular_yard['train'].level
            ref_truck = self.reefer_yard['truck'].level
            ref_train = self.reefer_yard['train'].level
            total_used = reg_truck + reg_train + ref_truck + ref_train
            total_capacity = (
                self.regular_yard['truck'].capacity + self.regular_yard['train'].capacity +
                self.reefer_yard['truck'].capacity + self.reefer_yard['train'].capacity
            )
            effective_total_capacity = total_capacity * self.effective_yard
            yard_frac = total_used / effective_total_capacity if effective_total_capacity > 0 else 0
            self.stats.resource_usage_by_minute['yard'][current_minute] = yard_frac

            yield self.env.timeout(1)  # record usage every minute

    def schedule_ships(self):
        """Schedule all ships based on the provided ship schedule"""
        for ship_data in self.ship_schedule:
            expected_arrival = ship_data["expected_arrival"]
            random_factor = random.normalvariate(1.0, self.arrival_time_variability["std"])
            time_delta = (random_factor - 1.0) * 60  # convert hours to minutes
            actual_arrival = max(0, expected_arrival + time_delta)
            ship_obj = Ship(
                self.env, 
                ship_data["name"], 
                ship_data["containers"], 
                expected_arrival,
                actual_arrival,
                self.container_types, 
                self.modal_split
            )
            self.ship_arrivals.append({
                "name": ship_data["name"],
                "containers": ship_data["containers"],
                "expected_arrival": expected_arrival,
                "actual_arrival": actual_arrival,
                "arrival_delta": actual_arrival - expected_arrival
            })
            ship_arrival_delay = actual_arrival - expected_arrival
            if ship_arrival_delay > 0 and self.stats.dwell_tracking_active:
                self.stats.log_dwell_components(ship_arrival_delay=ship_arrival_delay)
            self.env.process(self.schedule_ship_arrival(ship_obj, actual_arrival))
        
        # Add this yield statement to make the function a generator.
        yield self.env.timeout(0)
    
    def schedule_ship_arrival(self, ship, arrival_time):
        """Process for a scheduled ship arrival"""
        yield self.env.timeout(arrival_time)
        yield self.env.process(self.handle_ship(ship))

    def handle_ship(self, ship):
        arrival_time = self.env.now
        self.stats.log_ship_arrival()
        berth_req_start = self.env.now
        with self.berths.request() as berth_req:
            yield berth_req
            ship.berth_entry_time = self.env.now
            berth_wait = self.env.now - berth_req_start
            if self.stats.dwell_tracking_active:
                self.stats.log_wait_time('berth', berth_wait)
                self.stats.log_dwell_components(berth_wait_time=berth_wait)
            for c in ship.containers:
                c.berth_time = ship.berth_entry_time
            unload_procs = []
            for c in ship.containers:
                if self.stats.dwell_tracking_active:
                    self.stats.log_container_arrival(c.type)
                unload_procs.append(self.env.process(self.unload_container(c)))
            yield simpy.events.AllOf(self.env, unload_procs)
            yield self.env.timeout(self.berth_transition_time)
            ship.departure_time = self.env.now
        if self.stats.dwell_tracking_active:
            self.stats.log_wait_time('ship', self.env.now - arrival_time)
        for record in self.ship_arrivals:
            if record["name"] == ship.name:
                record["berth_entry_time"] = ship.berth_entry_time
                record["departure_time"] = ship.departure_time
                record["berth_wait_time"] = ship.berth_entry_time - ship.actual_arrival
                record["total_port_time"] = ship.departure_time - ship.actual_arrival
                break

    def unload_container(self, container):
        crane_req_start = self.env.now
        with self.cranes.request() as crane_req:
            yield crane_req
            crane_wait = self.env.now - crane_req_start
            if self.stats.dwell_tracking_active:
                self.stats.log_wait_time('crane', crane_wait)
            unload_time = random.normalvariate(self.unload_time_mean, self.unload_time_std)
            yield self.env.timeout(max(1, unload_time))
            self.env.process(self.process_container(container))

    def process_container(self, container):
        yard = self.reefer_yard if container.type == 'reefer' else self.regular_yard
        container_list = self.yard_containers[container.type][container.modal]
        if yard[container.modal].level < yard[container.modal].capacity:
            container.yard_entry_time = self.env.now
            
            if container.berth_time is not None:
                container_unloading = container.yard_entry_time - container.berth_time
                if container.from_vessel and self.stats.dwell_tracking_active:
                    self.stats.log_dwell_components(container_unloading=container_unloading)
            
            container.stacking_level = self.determine_stacking_level(container.type, container.modal)
            # Calculate and log the stacking retrieval time component
            stacking_time = self.calculate_stacking_retrieval_time(container.stacking_level)
            if container.from_vessel and self.stats.dwell_tracking_active:
                self.stats.log_stacking_retrieval_time(stacking_time)

            if container.from_vessel and self.stats.dwell_tracking_active:
                self.stats.log_stacking_level(container.stacking_level)
            
            container_list.append(container)
            self.all_containers.append(container)
            yield yard[container.modal].put(1)
            self.stats.update_yard_state(
                self.regular_yard['truck'].level,
                self.regular_yard['train'].level,
                self.reefer_yard['truck'].level,
                self.reefer_yard['train'].level
            )


            yard_storage = container.yard_waiting_time
            if container.from_vessel and self.stats.dwell_tracking_active:
                self.stats.log_dwell_components(yard_storage=yard_storage)
            
            container.ready_time = self.env.now + container.yard_waiting_time
            
            yield self.env.timeout(container.yard_waiting_time)
            container.departure_wait_start = self.env.now
            
            if container.modal == "truck":
                if container in container_list:
                    yield self.env.process(self.handle_truck_departure(container))
            
            if container.from_vessel and self.stats.dwell_tracking_active:
                self.stats.log_container(container.type, container.modal)
        else:
            self.stats.log_yard_full()

    def calculate_stacking_retrieval_time(self, stacking_level):
        total_used = (self.regular_yard['truck'].level + self.regular_yard['train'].level +
                    self.reefer_yard['truck'].level + self.reefer_yard['train'].level)
        total_capacity = (self.regular_yard['truck'].capacity + self.regular_yard['train'].capacity +
                        self.reefer_yard['truck'].capacity + self.reefer_yard['train'].capacity)
        yard_utilization = total_used / total_capacity if total_capacity > 0 else 0
        return calculate_stacking_retrieval_time(
            stacking_level,
            self.max_stacking_height,
            self.stacking_retrieval_base_time,
            self.stacking_retrieval_factor,
            yard_utilization
        )

    def handle_truck_departure(self, container):
        while True:
            absolute_hour = int(self.env.now / 60)
            hour_of_day = absolute_hour % 24

            # Check if the gate is open
            if hour_of_day < self.gate_hours["open"] or hour_of_day >= self.gate_hours["close"]:
                if hour_of_day >= self.gate_hours["close"]:
                    next_opening = ((24 - hour_of_day) + self.gate_hours["open"]) * 60
                else:
                    next_opening = (self.gate_hours["open"] - hour_of_day) * 60
                yield self.env.timeout(next_opening)
                continue

            # Ensure processing now will finish within operating hours.
            if (hour_of_day + (self.gate_hours["truck_pickup_time"] / 60)) >= self.gate_hours["close"]:
                wait_time = ((24 - hour_of_day) + self.gate_hours["open"]) * 60
                yield self.env.timeout(wait_time)
                continue

            # Process the truck at the gate with a fixed pickup time.
            with self.gate.request() as gate_req:
                yield gate_req
                yield self.env.timeout(self.gate_hours["truck_pickup_time"])
                container.departure_time = self.env.now
                # Log inland transport wait (departure wait) time component
                if container.from_vessel and self.stats.dwell_tracking_active:
                    departure_wait = container.departure_time - container.departure_wait_start
                    self.stats.log_dwell_components(departure_wait=departure_wait)


                # Remove container from the truck-bound yard.
                container_list = self.yard_containers[container.type]['truck']
                if container in container_list:
                    container_list.remove(container)
                if container.type == 'reefer':
                    yield self.reefer_yard['truck'].get(1)
                else:
                    yield self.regular_yard['truck'].get(1)

                self.stats.gate_departures_by_hour[absolute_hour] = (
                    self.stats.gate_departures_by_hour.get(absolute_hour, 0) + 1
                )

                # Log departure details if needed.
                ship_expected_arrival = None
                for ship_record in self.ship_arrivals:
                    if ship_record["name"] == container.id.split("_")[0]:
                        ship_expected_arrival = ship_record["expected_arrival"]
                        break
                if ship_expected_arrival is not None and container.from_vessel and self.stats.dwell_tracking_active:
                    total_dwell_time = container.departure_time - ship_expected_arrival
                    self.stats.log_dwell_time(container.type, total_dwell_time)

                truck_waiting = sum(
                    1 for t in self.yard_containers
                    for container in self.yard_containers[t]['truck']
                    if container.departure_wait_start is not None
                )
                self.stats.log_truck_waiting(self.env.now, truck_waiting)
                break
    

    def handle_train_departure(self):
        # Calculate and log the number of train-bound containers waiting
        waiting_dry = [c for c in self.yard_containers['dry']['train']
                    if c.modal == 'train' and c.ready_time <= self.env.now and c.departure_time is None]
        waiting_reefer = [c for c in self.yard_containers['reefer']['train']
                        if c.modal == 'train' and c.ready_time <= self.env.now and c.departure_time is None]
        total_waiting = len(waiting_dry) + len(waiting_reefer)
        self.stats.log_train_waiting(self.env.now, total_waiting)

        # Filter train-bound containers that are ready for departure
        dry_train_containers = waiting_dry  # already filtered above
        reefer_train_containers = waiting_reefer
        total_ready = len(dry_train_containers) + len(reefer_train_containers)

        if total_ready > 0:
            capacity_remaining = self.train_capacity
            loaded_dry = 0
            loaded_reefer = 0

            # Load dry containers first (sorted by ready time)
            for container in sorted(dry_train_containers, key=lambda c: c.ready_time):
                if capacity_remaining <= 0:
                    break
                container.departure_time = self.env.now
                loaded_dry += 1
                capacity_remaining -= 1
                self.yard_containers['dry']['train'].remove(container)

            # Then load reefer containers (sorted by ready time)
            for container in sorted(reefer_train_containers, key=lambda c: c.ready_time):
                if capacity_remaining <= 0:
                    break
                container.departure_time = self.env.now
                loaded_reefer += 1
                capacity_remaining -= 1
                self.yard_containers['reefer']['train'].remove(container)

            backlog = total_ready - (loaded_dry + loaded_reefer)
            self.stats.log_train_departure(
                dry_loaded=loaded_dry,
                reefer_loaded=loaded_reefer,
                capacity=self.train_capacity,
                backlog=backlog
            )
        else:
            self.stats.log_missed_train()

        # Wait until the next train departure, based on user input for trains per day
        interval_minutes = 1440 / self.trains_per_day
        yield self.env.timeout(interval_minutes)

    def determine_stacking_level(self, container_type, modal):
        """
        Determine the stacking level for a new container based on current yard utilization.
        Returns an integer between 1 and max_stacking_height.
        """
        # Select the appropriate yard based on container type.
        yard = self.reefer_yard if container_type == 'reefer' else self.regular_yard
        current_level = yard[modal].level
        max_capacity = yard[modal].capacity
        utilization = current_level / max_capacity if max_capacity > 0 else 0

        if self.max_stacking_height == 1:
            return 1

        # Calculate average stack height based on utilization.
        avg_stack_height = utilization * self.max_stacking_height

        # Build a probability distribution for levels 1 to max_stacking_height.
        probabilities = [0] * (self.max_stacking_height + 1)  # index 0 unused
        if avg_stack_height < 1:
            probabilities[1] = 1.0
        else:
            current_filling_level = min(math.ceil(avg_stack_height), self.max_stacking_height)
            fraction_of_current_level = avg_stack_height - (current_filling_level - 1)
            for i in range(1, current_filling_level):
                probabilities[i] = 1.0 / avg_stack_height if avg_stack_height > 0 else 0
            probabilities[current_filling_level] = fraction_of_current_level / avg_stack_height if avg_stack_height > 0 else 0

        levels = list(range(1, self.max_stacking_height + 1))
        valid_levels = [level for level, prob in zip(levels, probabilities[1:]) if prob > 0]
        valid_probs = [prob for prob in probabilities[1:] if prob > 0]

        if not valid_levels:
            return 1

        total_prob = sum(valid_probs)
        if total_prob > 0:
            valid_probs = [p / total_prob for p in valid_probs]

        return random.choices(valid_levels, weights=valid_probs, k=1)[0]

    def is_yard_empty(self):
        total_remaining = 0
        for container_type in ['dry', 'reefer']:
            for modal in ['truck', 'train']:
                total_remaining += len(self.yard_containers[container_type][modal])
        return total_remaining == 0
    
    def run(self):
        """
        Run the simulation until the last container has left the port.
        """
        # Schedule ship arrivals as a process.
        self.env.process(self.schedule_ships())
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Track time when the yard first becomes empty.
        yard_empty_since = None

        # Define an update interval in simulation minutes.
        update_interval = 10  # e.g., update UI every 10 minutes
        last_update = self.env.now

        while True:
            self.env.step()
            self.stats.update_yard_state(
                self.regular_yard['truck'].level,
                self.regular_yard['train'].level,
                self.reefer_yard['truck'].level,
                self.reefer_yard['train'].level
            )
            
            # Update progress based on the fraction of containers that have departed.
            departed_count = sum(1 for container in self.all_containers if container.departure_time is not None)
            if self.total_expected_containers:
                progress = departed_count / self.total_expected_containers
            else:
                progress = 1.0

            # Only update UI if the update interval has been exceeded.
            if self.env.now - last_update >= update_interval:
                progress_bar.progress(min(1.0, progress))
                last_update = self.env.now

            # Check if the yard is empty for an extended period (e.g., 60 minutes) and exit.
            if self.is_yard_empty():
                if yard_empty_since is None:
                    yard_empty_since = self.env.now
                else:
                    if self.env.now - yard_empty_since > 60:
                        break
            else:
                yard_empty_since = None

        progress_bar.progress(1.0)
        status_text.text(f"Simulation complete at {self.env.now:.1f} minutes")
        print("Simulation ended: Last container has left the port.")
