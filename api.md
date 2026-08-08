# Inventory Optimization System: Frontend Integration Guide

This guide describes how to connect the Flask REST API endpoints to a frontend client (such as a React, Vue, or Vanilla JS web app) for the **Inventory Optimization and Material Planning System**.

---

## 📡 API Server Details
* **Base URL:** `http://127.0.0.1:5000`
* **Protocol:** `HTTP`
* **Data Format:** `application/json`
* **CORS:** Enabled (`flask-cors` is configured to allow requests from any origin during development).

---

## ⚡ Endpoints & Frontend Code Snippets

### 1. Health Check
Use this to verify the frontend can communicate with the backend server.

* **Endpoint:** `GET /api/health`
* **JavaScript Fetch Example:**
```javascript
fetch('http://127.0.0.1:5000/api/health')
  .then(res => res.json())
  .then(data => {
    console.log("API Status:", data.status); // Output: "ok"
  })
  .catch(err => console.error("Server Offline:", err));
```

---

### 2. Retrieve Material Configurations & Usage History
Fetches a list of all 15 raw materials, including their current stock, lead times, and the last 90 days of daily demand logs. Use this on page load to populate selection dropdowns and default input fields.

* **Endpoint:** `GET /api/inventory/materials`
* **JavaScript Fetch Example:**
```javascript
fetch('http://127.0.0.1:5000/api/inventory/materials')
  .then(res => res.json())
  .then(materials => {
    // Populate your select dropdown
    materials.forEach(mat => {
      console.log(`Material: ${mat.material_id}, Stock: ${mat.current_stock}`);
    });
  });
```
* **Response Structure:**
```json
[
  {
    "material_id": "MAT_01",
    "current_stock": 3788,
    "lead_time_days": 7,
    "historical_usage_90": [292, 278, 172, 203, ... (90 items)]
  }
]
```

---

### 3. Run Inventory Optimization & Demand Forecasts
Submits current inventory levels and historical consumption to run the GBDT forecasting model and output mathematical stock recommendations.

* **Endpoint:** `POST /api/inventory/optimize`
* **JavaScript Fetch Example:**
```javascript
const payload = {
  material_id: "MAT_01",
  current_stock: 379.0,         // Value from user slider or ERP input
  lead_time_days: 7,            // Number of days to forecast forward
  historical_usage_90: [400.0, 395.0, ... (90 floats)], // Taken from selected material object
  order_cost: 50.0,             // Optional parameter
  holding_cost_per_unit: 2.0    // Optional parameter
};

fetch('http://127.0.0.1:5000/api/inventory/optimize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
})
  .then(res => {
    if (!res.ok) throw new Error("Optimization failed");
    return res.json();
  })
  .then(result => {
    console.log("Reorder Point:", result.reorder_point);
    console.log("Recommended Order:", result.recommended_order_qty);
    console.log("Stockout Risk Alert:", result.stockout_risk); // "HIGH" or "LOW"
    console.log("Forecast Curve:", result.forecasted_usage);   // Daily demand predictions
  });
```

---

## 💻 Full React Component Integration Example

Below is a complete, production-ready React component using standard hooks to load materials, simulate stock adjustments, run calculations, and render demand curves.

```jsx
import React, { useState, useEffect } from 'react';

export default function InventoryDashboard() {
  const [materials, setMaterials] = useState([]);
  const [selectedMat, setSelectedMat] = useState(null);
  const [stockLevel, setStockLevel] = useState(0);
  const [leadTime, setLeadTime] = useState(7);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // 1. Fetch materials config on mount
  useEffect(() => {
    fetch('http://127.0.0.1:5000/api/inventory/materials')
      .then(res => res.json())
      .then(data => {
        setMaterials(data);
        if (data.length > 0) {
          selectMaterial(data[0]);
        }
      })
      .catch(err => console.error("Error fetching materials:", err));
  }, []);

  const selectMaterial = (mat) => {
    setSelectedMat(mat);
    setStockLevel(mat.current_stock);
    setLeadTime(mat.lead_time_days);
  };

  const handleSelectChange = (e) => {
    const mat = materials.find(m => m.material_id === e.target.value);
    if (mat) selectMaterial(mat);
  };

  // 2. Submit Optimization request
  const runOptimization = () => {
    if (!selectedMat) return;
    setLoading(true);

    const payload = {
      material_id: selectedMat.material_id,
      current_stock: parseFloat(stockLevel),
      lead_time_days: parseInt(leadTime),
      historical_usage_90: selectedMat.historical_usage_90
    };

    fetch('http://127.0.0.1:5000/api/inventory/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        setResult(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h2>CodeSprint 2026: Material Planner</h2>
      
      {/* Selector */}
      <label>Select Material: </label>
      <select onChange={handleSelectChange} value={selectedMat?.material_id || ''}>
        {materials.map(m => (
          <option key={m.material_id} value={m.material_id}>{m.material_id}</option>
        ))}
      </select>

      {/* Slider */}
      <div style={{ margin: '20px 0' }}>
        <label>Current Stock: <strong>{stockLevel} units</strong></label>
        <input 
          type="range" 
          min="0" 
          max={selectedMat ? selectedMat.current_stock * 2 : 10000} 
          value={stockLevel} 
          onChange={(e) => setStockLevel(e.target.value)} 
          style={{ width: '100%', display: 'block' }}
        />
        <button onClick={() => setStockLevel(Math.round(selectedMat.current_stock * 0.1))}>
          Simulate Shortage (10% Stock)
        </button>
      </div>

      <button onClick={runOptimization} disabled={loading}>
        {loading ? 'Calculating...' : 'Run ML Optimizer'}
      </button>

      {/* Output Panel */}
      {result && (
        <div style={{ marginTop: '30px', border: '1px solid #ccc', padding: '20px' }}>
          <h3>Results: {result.material_id}</h3>
          <p>Stockout Risk: <strong style={{ color: result.stockout_risk === 'HIGH' ? 'red' : 'green' }}>{result.stockout_risk}</strong></p>
          <p>Reorder Point (ROP): {result.reorder_point} units</p>
          <p>Safety Stock Buffer: {result.safety_stock} units</p>
          <p>EOQ Size: {result.eoq} units</p>
          <p>Order Quantity: <strong>{result.recommended_order_qty} units</strong></p>
          <h4>Forecasted Lead-Time Demand Curve:</h4>
          <ul>
            {result.forecasted_usage.map((val, idx) => (
              <li key={idx}>Day {idx + 1}: {val} units</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```
