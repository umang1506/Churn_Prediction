import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import hashlib

def generate_synthetic_churn_data(n_samples=2000, seed=42):
    """Generate realistic synthetic churn data for training."""
    np.random.seed(seed)
    
    recency = np.random.randint(1, 365, n_samples)
    frequency = np.random.randint(1, 100, n_samples)
    total_spend = np.random.uniform(100, 10000, n_samples)
    avg_order_value = total_spend / frequency
    lifetime = np.random.randint(0, 730, n_samples)
    cancellation_ratio = np.random.uniform(0, 0.5, n_samples)
    return_ratio = np.random.uniform(0, 0.3, n_samples)
    total_quantity = frequency * np.random.randint(1, 5, n_samples)
    
    # Churn probability logic (Recency is primary factor)
    # Higher recency = higher churn
    # Lower frequency = higher churn
    # Higher cancellations = higher churn
    
    prob = (0.5 * recency / 365) + \
           (0.3 * (1 - frequency / 100)) + \
           (0.2 * cancellation_ratio) + \
           (0.1 * return_ratio)
    
    # Random noise
    prob += np.random.normal(0, 0.1, n_samples)
    
    churn = (prob > 0.6).astype(int)
    
    data = pd.DataFrame({
        'recency': recency,
        'frequency': frequency,
        'total_spend': total_spend,
        'avg_order_value': avg_order_value,
        'lifetime': lifetime,
        'cancellation_ratio': cancellation_ratio,
        'return_ratio': return_ratio,
        'total_quantity': total_quantity,
        'churn': churn
    })
    
    return data

def train_and_save_model():
    """Train Random Forest and XGBoost models and save the ensemble."""
    print("Generating training data...")
    data = generate_synthetic_churn_data()
    
    X = data.drop('churn', axis=1)
    y = data['churn']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Random Forest
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    
    # XGBoost
    xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
    xgb_model.fit(X_train, y_train)
    
    # Predict and compare performance
    rf_acc = accuracy_score(y_test, rf_model.predict(X_test))
    xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test))
    
    print(f"Random Forest Accuracy: {rf_acc:.4f}")
    print(f"XGBoost Accuracy: {xgb_acc:.4f}")
    
    # Ensure directory exists
    model_dir = os.path.join(os.getcwd(), 'models')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        
    model_path = os.path.join(model_dir, 'churn_model.pkl')
    
    # Save the ensemble/preferred model
    # We'll save a dictionary containing both or the best one.
    model_payload = {
        'model': rf_model, # RF as primary due to simplicity/interpretability
        'xgb': xgb_model,
        'feature_names': X.columns.tolist()
    }
    
    joblib.dump(model_payload, model_path)
    print(f"Model saved to: {model_path}")

if __name__ == "__main__":
    train_and_save_model()
