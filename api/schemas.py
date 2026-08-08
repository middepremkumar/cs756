from marshmallow import Schema, fields, validate, ValidationError


class OptimizationRequestSchema(Schema):
    material_id = fields.Str(required=True)
    current_stock = fields.Float(required=True)
    lead_time_days = fields.Int(required=True, validate=validate.Range(min=1))
    historical_usage_90 = fields.List(fields.Float(), required=True)
    order_cost = fields.Float(load_default=50.0)
    holding_cost_per_unit = fields.Float(load_default=2.0)
