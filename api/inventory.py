import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from core.pipeline import forecast_demand
from core.inventory_logic import recommend
from api.schemas import OptimizationRequestSchema

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api")

_schema = OptimizationRequestSchema()
logger = logging.getLogger(__name__)


@inventory_bp.get("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200


@inventory_bp.get("/inventory/materials")
def get_materials():
    import pandas as pd
    import json
    import os
    data_path = "inventory_data.csv"
    metadata_path = "material_metadata.json"
    if not os.path.exists(data_path) or not os.path.exists(metadata_path):
        return jsonify({"error": "Dataset or metadata not found. Please run generate_data.py first."}), 404
        
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
        
    materials_list = []
    for mat_id in sorted(df['material_id'].unique()):
        df_mat = df[df['material_id'] == mat_id].sort_values('date')
        latest_row = df_mat.iloc[-1]
        history = df_mat['units_used'].tolist()
        materials_list.append({
            "material_id": mat_id,
            "current_stock": int(latest_row['current_stock']),
            "lead_time_days": int(metadata[mat_id]['lead_time']),
            "historical_usage_90": [int(v) for v in history[-90:]]
        })
    return jsonify(materials_list), 200


@inventory_bp.get("/openapi.json")
def openapi():
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Inventory Optimization & Material Planning System API",
            "version": "1.0.0",
            "description": "API for predicting raw material demand and optimizing warehouse stock levels (CodeSprint 2026)."
        },
        "paths": {
            "/api/health": {
                "get": {
                    "summary": "Health Check",
                    "description": "Verify backend service availability status.",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "ok"},
                                            "timestamp": {"type": "string", "format": "date-time"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/inventory/materials": {
                "get": {
                    "summary": "Retrieve Material Configurations & Logs",
                    "description": "Get latest stock levels, lead times, and 90-day history for all 15 materials.",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "material_id": {"type": "string", "example": "MAT_01"},
                                                "current_stock": {"type": "integer", "example": 3788},
                                                "lead_time_days": {"type": "integer", "example": 7},
                                                "historical_usage_90": {
                                                    "type": "array",
                                                    "items": {"type": "integer"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/inventory/optimize": {
                "post": {
                    "summary": "Optimize Inventory Recommendations",
                    "description": "Executes GBDT demand forecasts and calculates safety stock, ROP, EOQ, and risk.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["material_id", "current_stock", "lead_time_days", "historical_usage_90"],
                                    "properties": {
                                        "material_id": {"type": "string", "example": "MAT_01"},
                                        "current_stock": {"type": "number", "example": 379.0},
                                        "lead_time_days": {"type": "integer", "example": 7},
                                        "historical_usage_90": {
                                            "type": "array",
                                            "items": {"type": "number"}
                                        },
                                        "order_cost": {"type": "number", "default": 50.0},
                                        "holding_cost_per_unit": {"type": "number", "default": 2.0}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Optimization recommendation generated successfully.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "material_id": {"type": "string", "example": "MAT_01"},
                                            "current_stock": {"type": "integer", "example": 379},
                                            "safety_stock": {"type": "integer", "example": 441},
                                            "reorder_point": {"type": "integer", "example": 3425},
                                            "eoq": {"type": "integer", "example": 2789},
                                            "recommended_order_qty": {"type": "integer", "example": 2789},
                                            "stockout_risk": {"type": "string", "example": "HIGH"},
                                            "forecasted_usage": {
                                                "type": "array",
                                                "items": {"type": "number"},
                                                "example": [372.88, 366.01, 391.8, 392.72, 387.07, 380.59, 375.04]
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Validation error (e.g. invalid inputs or history length < 90)."
                        },
                        "404": {
                            "description": "Forecasting model not found for material."
                        }
                    }
                }
            }
        }
    }
    return jsonify(spec), 200


@inventory_bp.post("/inventory/optimize")
def optimize():
    try:
        payload = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if len(payload["historical_usage_90"]) < 90:
        return jsonify({
            "error": "Minimum 90 days of usage history is required for safety stock calculations."
        }), 400

    material_id = payload["material_id"]
    historical_usage_30 = payload["historical_usage_90"][-30:]

    try:
        forecast = forecast_demand(
            material_id=material_id,
            historical_usage_30=historical_usage_30,
            lead_time_days=payload["lead_time_days"],
            models_dir="models",
            reference_date=datetime.now(),
        )

        result = recommend(
            material_id=material_id,
            current_stock=payload["current_stock"],
            forecasted_usage=forecast,
            lead_time_days=payload["lead_time_days"],
            historical_usage_90=payload["historical_usage_90"],
            order_cost=payload["order_cost"],
            holding_cost_per_unit=payload["holding_cost_per_unit"],
        )

        result["forecasted_usage"] = [round(v, 2) for v in forecast]

        logger.info(
            "optimize | material_id=%s stockout_risk=%s",
            material_id,
            result["stockout_risk"],
        )
        return jsonify(result), 200

    except FileNotFoundError:
        logger.warning("optimize | model not found for material_id=%s", material_id)
        return jsonify({
            "error": f"Forecasting model for material '{material_id}' was not found. Please train models first."
        }), 404

    except Exception as exc:
        logger.exception("optimize | unexpected error for material_id=%s", material_id)
        return jsonify({"error": str(exc)}), 500
