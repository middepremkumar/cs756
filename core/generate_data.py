import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_synthetic_data(output_path="inventory_data.csv"):
    np.random.seed(42)
    
    num_materials = 15
    num_days = 730
    start_date = datetime(2024, 1, 1)
    
    # Generate list of dates
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    
    material_ids = [f"MAT_{i:02d}" for i in range(1, num_materials + 1)]
    
    # Store material properties for simulation
    material_props = {}
    for mat_id in material_ids:
        base_demand = np.random.uniform(100, 900)
        lead_time = np.random.randint(3, 11)  # 3 to 10 days
        
        # 3 to 5 random shock events
        num_shocks = np.random.randint(3, 6)
        shocks = []
        for _ in range(num_shocks):
            shock_start = np.random.randint(30, num_days - 15)
            shock_dur = np.random.randint(3, 8)
            shock_mult = np.random.uniform(1.8, 3.0)
            shocks.append({
                "start": shock_start,
                "end": shock_start + shock_dur,
                "multiplier": shock_mult
            })
            
        # 1 to 2 supply disruption periods
        num_disruptions = np.random.randint(1, 3)
        disruptions = []
        for _ in range(num_disruptions):
            disr_start = np.random.randint(30, num_days - 20)
            disr_dur = np.random.randint(7, 16)
            disruptions.append({
                "start": disr_start,
                "end": disr_start + disr_dur,
                "delay": np.random.randint(4, 11)
            })
            
        material_props[mat_id] = {
            "base_demand": base_demand,
            "lead_time": lead_time,
            "shocks": shocks,
            "disruptions": disruptions
        }
    
    # Generate records
    all_records = []
    
    for mat_id, props in material_props.items():
        base_demand = props["base_demand"]
        lead_time = props["lead_time"]
        shocks = props["shocks"]
        disruptions = props["disruptions"]
        
        # 1. Generate demand timeline
        demands = []
        for t in range(num_days):
            # Seasonality: weekly (period 7) + yearly (period 365)
            weekly_season = 0.15 * base_demand * np.sin(2 * np.pi * t / 7)
            yearly_season = 0.25 * base_demand * np.sin(2 * np.pi * t / 365)
            noise = np.random.normal(0, 0.1 * base_demand)
            
            day_demand = base_demand + weekly_season + yearly_season + noise
            
            # Apply demand shocks
            for shock in shocks:
                if shock["start"] <= t <= shock["end"]:
                    day_demand *= shock["multiplier"]
            
            day_demand = max(5.0, day_demand)
            demands.append(int(round(day_demand)))
            
        # 2. Simulate inventory levels
        # Initial stock is 3x lead-time demand + extra safety stock
        current_stock = int(round(base_demand * lead_time * 3.5))
        reorder_point = int(round(base_demand * lead_time * 1.5))
        order_qty = int(round(base_demand * 15))  # Reorder ~15 days of demand
        
        pending_orders = []  # List of dicts: {"arrival_day": int, "qty": int}
        
        for t in range(num_days):
            units_used = demands[t]
            
            # Process deliveries arriving at the start of the day
            arrived_qty = 0
            remaining_orders = []
            for order in pending_orders:
                if order["arrival_day"] <= t:
                    arrived_qty += order["qty"]
                else:
                    remaining_orders.append(order)
            pending_orders = remaining_orders
            current_stock += arrived_qty
            
            # Deplete stock
            current_stock = max(0, current_stock - units_used)
            
            # Check if we need to order (continuous review)
            # Standard order check: current stock + pending orders
            total_inventory_position = current_stock + sum(order["qty"] for order in pending_orders)
            
            if total_inventory_position < reorder_point:
                # Determine lead time and check if there's an active supply disruption
                actual_lead_time = lead_time
                for disr in disruptions:
                    if disr["start"] <= t <= disr["end"]:
                        actual_lead_time += disr["delay"]
                        break
                
                arrival_day = t + actual_lead_time
                pending_orders.append({
                    "arrival_day": arrival_day,
                    "qty": order_qty
                })
            
            all_records.append({
                "date": dates[t].strftime("%Y-%m-%d"),
                "material_id": mat_id,
                "units_used": units_used,
                "current_stock": current_stock
            })
            
    # Save metadata for downstream use
    import json
    metadata_path = "material_metadata.json"
    meta_dict = {
        mat_id: {
            "base_demand": int(round(props["base_demand"])),
            "lead_time": int(props["lead_time"])
        }
        for mat_id, props in material_props.items()
    }
    with open(metadata_path, 'w') as f:
        json.dump(meta_dict, f, indent=4)
    print(f"Metadata saved to '{metadata_path}'.")

    df = pd.DataFrame(all_records)
    df.to_csv(output_path, index=False)
    print(f"Dataset successfully created at '{output_path}' with {len(df)} rows.")
    print(f"Columns: {list(df.columns)}")
    
if __name__ == "__main__":
    generate_synthetic_data()
