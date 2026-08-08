import numpy as np

def recommend(material_id, current_stock, forecasted_usage, lead_time_days, historical_usage_90, order_cost=50, holding_cost_per_unit=2):
    """
    Calculate inventory optimization metrics and recommend replenishment orders.
    
    Parameters:
    - material_id (str): Unique identifier for the material
    - current_stock (float): Current units of stock in inventory
    - forecasted_usage (list or np.ndarray): Daily usage forecasts for the lead-time window
    - lead_time_days (int): Lead time in days for replenishment
    - historical_usage_90 (list or np.ndarray): Last 90 days of historical units_used from training data
    - order_cost (float): Cost to place one order (default: 50)
    - holding_cost_per_unit (float): Annual holding cost per unit (default: 2)
    
    Returns:
    - dict: Recommendations with keys:
      - reorder_point: Threshold stock level to place a new order
      - recommended_order_qty: EOQ if stock < ROP, else 0
      - stockout_risk: "HIGH" or "LOW"
      - safety_stock: Safety stock level
      - eoq: Economic Order Quantity
    """
    forecasted_usage = np.array(forecasted_usage)
    if len(forecasted_usage) == 0:
        raise ValueError("forecasted_usage must not be empty")
        
    mean_usage = np.mean(forecasted_usage)
    std_usage = np.std(historical_usage_90)
    
    # 1. Safety Stock (SS)
    # Z-score for 95% service level is 1.645.
    # std_usage is standard deviation of daily demand from historical 90 days.
    # Safety stock over lead time is z * std_daily * sqrt(lead_time_days).
    z_score = 1.645
    safety_stock = z_score * std_usage * np.sqrt(lead_time_days)
    
    # 2. Reorder Point (ROP)
    reorder_point = (mean_usage * lead_time_days) + safety_stock
    
    # 3. Economic Order Quantity (EOQ)
    # Annual demand = daily average usage * 365 days
    annual_demand = mean_usage * 365
    eoq = np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit)
    
    # 4. Stockout Risk
    stockout_risk = "HIGH" if current_stock < reorder_point else "LOW"
    
    # 5. Recommended Order Quantity
    recommended_order_qty = eoq if current_stock < reorder_point else 0.0
    
    return {
        "material_id": material_id,
        "current_stock": int(round(current_stock)),
        "safety_stock": int(round(safety_stock)),
        "reorder_point": int(round(reorder_point)),
        "eoq": int(round(eoq)),
        "recommended_order_qty": int(round(recommended_order_qty)),
        "stockout_risk": stockout_risk
    }
