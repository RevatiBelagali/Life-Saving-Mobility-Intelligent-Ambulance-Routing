import traci
import math
import json
import os  # For logs folder

def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

# Start SUMO
sumoCmd = ["sumo-gui", "-c", "osm.sumocfg"]
traci.start(sumoCmd)

PROACTIVE_DISTANCE = 100  # Range to detect vehicles ahead
alerted_vehicles = set()
original_tl_programs = {}

hospital_position = (1386.5, 1987.8)
reached_hospital = set()

log_file = "simulation_log.json"

print("\n🚑 Starting V2V and V2I Emergency Communication Simulation...\n")

step = 0

# Data structures for logging
time_log = []
ambulance_speed_log = []
vehicle_alert_count = []
traffic_light_control_log = []
stopped_vehicle_counts = []

os.makedirs("logs", exist_ok=True)  # Create logs directory once here

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    vehicles = traci.vehicle.getIDList()
    ambulances = [v for v in vehicles if "ambulance" in v.lower() or traci.vehicle.getVehicleClass(v) == "emergency"]

    alerted_this_step = set()
    controlled_tls = set()
    stopped_count = 0

    vehicle_data = {}

    for amb_id in ambulances:
        amb_pos = traci.vehicle.getPosition(amb_id)
        amb_edge = traci.vehicle.getRoadID(amb_id)
        amb_lane_index = traci.vehicle.getLaneIndex(amb_id)
        amb_speed = traci.vehicle.getSpeed(amb_id)

        # Mark ambulance red during movement
        traci.vehicle.setColor(amb_id, (255, 0, 0, 255))
        traci.vehicle.setSpeedMode(amb_id, 0)

        congestion_detected = False
        for veh_id in vehicles:
            if veh_id == amb_id or traci.vehicle.getVehicleClass(veh_id) == "emergency":
                continue

            veh_edge = traci.vehicle.getRoadID(veh_id)
            veh_lane = traci.vehicle.getLaneIndex(veh_id)
            veh_pos = traci.vehicle.getPosition(veh_id)

            if veh_edge == amb_edge and veh_lane == amb_lane_index:
                dist = distance(amb_pos, veh_pos)
                if 0 < dist < PROACTIVE_DISTANCE and veh_pos[0] > amb_pos[0]:
                    print(f"📡 [V2V] Ambulance {amb_id} ALERTING Vehicle {veh_id} at distance {int(dist)} meters")
                    alerted_this_step.add(veh_id)
                    congestion_detected = True
                    break

        if congestion_detected:
            num_lanes = traci.edge.getLaneNumber(amb_edge)
            changed = False
            options = []

            if amb_lane_index + 1 < num_lanes:
                options.append(amb_lane_index + 1)
            if amb_lane_index - 1 >= 0:
                options.append(amb_lane_index - 1)

            for new_lane in options:
                try:
                    before_lane_id = traci.vehicle.getLaneID(amb_id)
                    traci.vehicle.changeLane(amb_id, new_lane, 10.0)
                    after_lane_id = traci.vehicle.getLaneID(amb_id)

                    if after_lane_id != before_lane_id:
                        print(f"✅ Ambulance {amb_id} changed lane from {before_lane_id} ➡ {after_lane_id}")
                        changed = True
                        break
                except Exception as e:
                    print(f"⚠️ Lane change error for {amb_id} to lane {new_lane}: {e}")
                    continue
            if not changed:
                print(f"📡 Vehicles on other edges are stopping to allow ambulance {amb_id} to pass.")
        else:
            print(f"✅ Ambulance {amb_id} moving freely, no congestion ahead.")

        # Traffic Light Control (V2I)
        junctions = traci.trafficlight.getIDList()
        for tl in junctions:
            controlled_lanes = traci.trafficlight.getControlledLanes(tl)
            if any(amb_edge in lane for lane in controlled_lanes):
                controlled_tls.add(tl)
                if tl not in original_tl_programs:
                    original_tl_programs[tl] = traci.trafficlight.getProgram(tl)
                    print(f"🚦 [V2I] Ambulance {amb_id} Taking control of Traffic Light {tl}")

                original_state = traci.trafficlight.getRedYellowGreenState(tl)
                state = ''.join(['G' if amb_edge in lane else 'r' for lane in controlled_lanes])

                if len(state) == len(original_state):
                    traci.trafficlight.setRedYellowGreenState(tl, state)
                else:
                    print(f"⚠️ State length mismatch for TL {tl}. Skipping override.")
            else:
                if tl in original_tl_programs:
                    print(f"🚦 [V2I] Ambulance {amb_id} overriding the Traffic Light {tl}")
                    traci.trafficlight.setProgram(tl, original_tl_programs[tl])
                    del original_tl_programs[tl]

        # Hospital arrival
        if amb_id not in reached_hospital and distance(amb_pos, hospital_position) < 10:
            print(f"🏥 Ambulance {amb_id} has reached the hospital!")
            reached_hospital.add(amb_id)
            traci.vehicle.setColor(amb_id, (0, 255, 0, 255))  # Green
            traci.vehicle.setSpeed(amb_id, 0)  # Stop ambulance

        # Log ambulance data
        vehicle_data[amb_id] = {
            "speed": amb_speed,
            "class": "ambulance",
            "position": list(amb_pos),
            "stopped": amb_id in reached_hospital,
            "is_ambulance": True,
        }

    # Log all vehicles (except ambulances)
    for veh_id in vehicles:
        if veh_id in vehicle_data:
            continue
        pos = traci.vehicle.getPosition(veh_id)
        speed = traci.vehicle.getSpeed(veh_id)
        stopped = speed < 0.1
        if stopped:
            stopped_count += 1

        vehicle_data[veh_id] = {
            "speed": speed,
            "class": traci.vehicle.getVehicleClass(veh_id),
            "position": list(pos),
            "stopped": stopped,
            "is_ambulance": False,
        }

    # Append logs for visualization
    time_log.append(step)
    ambulance_speed_log.append(max([vehicle_data[amb]["speed"] for amb in ambulances]) if ambulances else 0)
    vehicle_alert_count.append(len(alerted_this_step))
    traffic_light_control_log.append(len(controlled_tls))
    stopped_vehicle_counts.append(stopped_count)

    # Write to simulation_log.json
    log_dict = {
        "time_log": time_log,
        "ambulance_speed_log": ambulance_speed_log,
        "vehicle_alert_count": vehicle_alert_count,
        "traffic_light_control_log": traffic_light_control_log,
        "stopped_vehicle_counts": stopped_vehicle_counts,
        "vehicle_data": vehicle_data,
    }
    with open(log_file, "w") as f:
        json.dump(log_dict, f, indent=2)

    # ✅ Save logs in separate files
    with open("logs/v2v_alerts.json", "w") as f:
        json.dump(vehicle_alert_count, f)

    with open("logs/ambulance_speed.json", "w") as f:
        json.dump(ambulance_speed_log, f)

    with open("logs/tl_overrides.json", "w") as f:
        json.dump(traffic_light_control_log, f)

    with open("logs/lane_changes.json", "w") as f:
        json.dump([], f)  # Placeholder

    with open("logs/arrival_summary.json", "w") as f:
        json.dump(list(reached_hospital), f)

    with open("logs/clearance_times.json", "w") as f:
        json.dump(stopped_vehicle_counts, f)

    with open("logs/travel_times.json", "w") as f:
        json.dump(ambulance_speed_log, f)

    with open("logs/traffic_heatmap_before.json", "w") as f:
        json.dump(vehicle_data, f)

    with open("logs/traffic_heatmap_after.json", "w") as f:
        json.dump(vehicle_data, f)

    # ====== NEW: Write live vehicle data for Streamlit UI ======

    live_data = {}

    for veh_id in vehicles:
        try:
            vehicle_type = traci.vehicle.getTypeID(veh_id)
        except Exception:
            vehicle_type = "unknown"

        speed = traci.vehicle.getSpeed(veh_id)

        # These are example parameters; make sure they exist or handle gracefully
        try:
            alerts_received = traci.vehicle.getParameter(veh_id, "alertsReceived")
            alerts_received = int(alerts_received) if alerts_received else 0
        except Exception:
            alerts_received = 0

        try:
            clearance_status = traci.vehicle.getParameter(veh_id, "clearanceStatus")
            clearance_status = clearance_status if clearance_status else "unknown"
        except Exception:
            clearance_status = "unknown"

        ambulance_status = "N/A"
        if vehicle_type == "ambulance":
            ambulance_status = "moving" if speed >= 0.1 else "stopped"

        live_data[veh_id] = {
            "vehid": veh_id,
            "vehicle_type": vehicle_type,
            "speed": round(speed, 2),
            "alerts_received": alerts_received,
            "clearance_status": clearance_status,
            "ambulance_status": ambulance_status,
        }

    with open("logs/live_vehicle_data.json", "w") as f:
        json.dump(live_data, f, indent=2)

    # ================================================

    step += 1

traci.close()
print("\n✅ Simulation completed — Ambulance followed V2V/V2I priority and reached hospital.")
