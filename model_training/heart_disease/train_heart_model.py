import os
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

def main() -> None: # Train RandomForest model ->  then save it as a pickle file with the feature names
    # Resolve project paths
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]  # go up 2 levels to project root
    
    data_path = project_root / "app" / "data" / "datasets" / "Heart Disease UCI.csv"
    model_dir = project_root / "app" / "data" / "saved_models"
    model_dir.mkdir(parents = True, exist_ok = True)
    model_path = model_dir / "heart_model.pkl"
    
    print(f"[INFO] Project root: {project_root}")
    print(f"[INFO] Loading dataset from: {data_path}")
    
    # Load dataset
    if not data_path.exists():
        raise FileNotFoundError(
            f"Could not find dataset at {data_path}. "
            f"Make sure your CSV is placed there and named 'Heart Disease UCI.csv'."
        )

    df = pd.read_csv(data_path)
    print(f"[INFO] Dataset shape: {df.shape}")
    print("[INFO] Columns:", list(df.columns))
    
    # Define features (X) and target (y)
    if "target" not in df.columns:
        raise KeyError(
            "Column 'target' not found in dataset. "
            "Please ensure the label column is named 'target'."
        )

    X = df.drop(columns = ["target"])
    y = df["target"]    # target (0 = no disease, 1 = disease)
    feature_names = list(X.columns)
    print("[INFO] Using features:", feature_names)
    
    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size = 0.2,
        random_state = 42,
        stratify = y,
    )
    print(f"[INFO] Train size: {X_train.shape[0]}")
    print(f"[INFO] Test size:  {X_test.shape[0]}")
    
    # Create and train RandomForest model
    rf = RandomForestClassifier(
        n_estimators = 200,
        max_depth = None,
        random_state = 42,
        class_weight = "balanced",
        n_jobs = -1,
    )

    print("[INFO] Training RandomForest model...")
    rf.fit(X_train, y_train)
    
    # Evaluate model
    y_train_pred = rf.predict(X_train)
    y_test_pred = rf.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    print(f"[RESULT] Train accuracy: {train_acc:.4f}")
    print(f"[RESULT] Test  accuracy: {test_acc:.4f}")
    print("\n[RESULT] Classification report (test set):")
    print(classification_report(y_test, y_test_pred))

    # Save model + feature names
    model_bundle = {
        "model": rf,
        "feature_names": feature_names,
    }
    joblib.dump(model_bundle, model_path)
    print(f"[INFO] Model saved to: {model_path}")

if __name__ == "__main__":
    main()
    
    
    
    