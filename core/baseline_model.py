import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

def prepare_features(df_material):
    """
    Generate lag and rolling features for a single material's dataset.
    Ensures no data leakage by shifting the rolling calculations.
    """
    df = df_material.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Lag features
    df['units_used_lag_1'] = df['units_used'].shift(1)
    df['units_used_lag_7'] = df['units_used'].shift(7)
    df['units_used_lag_14'] = df['units_used'].shift(14)
    df['units_used_lag_30'] = df['units_used'].shift(30)
    
    # Rolling features (shifted by 1 to prevent data leakage)
    df['rolling_mean_7'] = df['units_used'].shift(1).rolling(window=7).mean()
    df['rolling_mean_30'] = df['units_used'].shift(1).rolling(window=30).mean()
    df['rolling_std_7'] = df['units_used'].shift(1).rolling(window=7).std()
    
    # Time features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    
    return df

def train_baseline_models(data_path="inventory_data.csv", models_dir="models"):
    # Ensure models directory exists
    os.makedirs(models_dir, exist_ok=True)
    
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Source data file '{data_path}' not found. Please run generate_data.py first.")
        
    df = pd.read_csv(data_path)
    materials = df['material_id'].unique()
    
    feature_cols = [
        'units_used_lag_1', 'units_used_lag_7', 'units_used_lag_14', 'units_used_lag_30',
        'rolling_mean_7', 'rolling_mean_30', 'rolling_std_7',
        'day_of_week', 'month'
    ]
    target_col = 'units_used'
    
    maes = {}
    
    print("Starting training of baseline forecasting models...")
    print("-" * 60)
    print(f"{'Material ID':<15} | {'Train Size':<10} | {'Test Size':<10} | {'Test MAE':<10}")
    print("-" * 60)
    
    for mat_id in sorted(materials):
        df_mat = df[df['material_id'] == mat_id].copy()
        
        # Prepare features
        df_feats = prepare_features(df_mat)
        
        # Drop rows with NaN (first 30 days due to lags/rolling stats)
        df_feats = df_feats.dropna().reset_index(drop=True)
        
        # Chronological split (80% train, 20% test)
        split_idx = int(len(df_feats) * 0.8)
        train_df = df_feats.iloc[:split_idx]
        test_df = df_feats.iloc[split_idx:]
        
        X_train, y_train = train_df[feature_cols], train_df[target_col]
        X_test, y_test = test_df[feature_cols], test_df[target_col]
        
        # Train Gradient Boosting Regressor
        model = GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=4, learning_rate=0.1)
        model.fit(X_train, y_train)
        
        # Predict and evaluate
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        maes[mat_id] = mae
        
        # Save model
        model_path = os.path.join(models_dir, f"{mat_id}_baseline.pkl")
        joblib.dump(model, model_path)
        
        print(f"{mat_id:<15} | {len(train_df):<10} | {len(test_df):<10} | {mae:<10.2f}")
        
    mean_mae = np.mean(list(maes.values()))
    print("-" * 60)
    print(f"Average Test MAE across all materials: {mean_mae:.2f}")
    
if __name__ == "__main__":
    train_baseline_models()
