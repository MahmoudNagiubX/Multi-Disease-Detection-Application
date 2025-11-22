from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.core.managers.database_manager import db_manager
from app.core.managers.model_manager import model_manager

class PredictionService:    # Handles prediction logic for heart disease and brain tumor
    # Uses ModelManager to access models and DatabaseManager to log results
    def __init__(self) -> None:
        self.db = db_manager
        self.models = model_manager
        
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    def _parse_float(self, value: str, default: float = 0.0) -> float: 
        # Safely parse a string to float. Returns default if parsing fails
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    
    def predict_heart_disease(self, form_data: Dict[str, str], user_id: Optional[int]) -> Dict[str, Any]:
        """
        Take raw form data -> build feature dict -> call HeartDiseaseModel ->
        log prediction (if user_id) -> return structured result + log_id.
        """

        # --------------------
        # 1) Parse inputs
        # --------------------
        def _parse_binary(val: Optional[str]) -> float:
            if val is None:
                return 0.0
            val = str(val).strip().lower()
            if val in ("1", "yes", "y", "true"):
                return 1.0
            if val in ("0", "no", "n", "false"):
                return 0.0
            return 0.0

        # --- Parse numeric fields (adapt to your form names) ---
        age = self._parse_float(form_data.get("age"))
        trestbps = self._parse_float(form_data.get("trestbps"))
        chol = self._parse_float(form_data.get("chol"))
        thalach = self._parse_float(form_data.get("thalach"))
        oldpeak = self._parse_float(form_data.get("oldpeak"))
        ca = self._parse_float(form_data.get("ca"))

        # --- Parse binary / categorical fields ---
        sex = _parse_binary(form_data.get("sex"))
        fbs = _parse_binary(form_data.get("fbs"))
        exang = _parse_binary(form_data.get("exang"))

        # Chest pain type, restecg, slope, thal – assuming they come as numeric codes
        cp = self._parse_float(form_data.get("cp"))
        restecg = self._parse_float(form_data.get("restecg"))
        slope = self._parse_float(form_data.get("slope"))
        thal = self._parse_float(form_data.get("thal"))

        # Build features dict (keys must match training script)
        features = {
            "age": age,
            "sex": sex,
            "cp": cp,
            "trestbps": trestbps,
            "chol": chol,
            "fbs": fbs,
            "restecg": restecg,
            "thalach": thalach,
            "exang": exang,
            "oldpeak": oldpeak,
            "slope": slope,
            "ca": ca,
            "thal": thal,
        }

        # --------------------
        # 2) Predict
        # --------------------
        heart_model = self.models.get_heart_model()
        risk_label, probability = heart_model.predict(features)

        # Short summary for DB
        input_summary = (
            f"age={age}, sex={sex}, cp={cp}, trestbps={trestbps}, chol={chol}, "
            f"fbs={fbs}, restecg={restecg}, thalach={thalach}, exang={exang}, "
            f"oldpeak={oldpeak}, slope={slope}, ca={ca}, thal={thal}"
        )

        # --------------------
        # 3) Log to DB + get log_id
        # --------------------
        log_id: Optional[int] = None

        if user_id is not None:
            # Insert log and get the inserted row ID in the same transaction
            log_id = self.db.execute_and_get_id(
                """
                INSERT INTO prediction_logs (
                    user_id, model_type, input_summary,
                    prediction_result, probability, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "heart_disease",
                    input_summary,
                    risk_label,
                    float(probability),
                    self._now_iso(),
                ),
            )

        # --------------------
        # 4) Return result dict (used in templates)
        # --------------------
        return {
            "risk_label": risk_label,
            "probability": probability,
            "features": features,
            "input_summary": input_summary,
            "suggestion": self._generate_heart_suggestion(risk_label),
            "log_id": log_id,
        }

    def _generate_heart_suggestion(self, risk_label: str) -> str: # Treatment suggestion
        if risk_label == "High":
            return (
                "Your risk is estimated as HIGH. "
                "This is not a diagnosis, but you should strongly consider "
                "speaking with a cardiologist and getting full medical tests."
            )
        elif risk_label == "Medium":
            return (
                "Your risk is estimated as MEDIUM. "
                "Consider regular check-ups, monitoring blood pressure and cholesterol, "
                "and discussing lifestyle changes with a healthcare professional."
            )
        else:
            return (
                "Your risk is estimated as LOW. "
                "Maintain a healthy lifestyle, exercise regularly, and keep up with periodic check-ups."
            )
    
    def predict_brain_tumor(self, image_path: str, user_id: Optional[int]) -> Dict[str, Any]:
        # Take an MRI image path -> call BrainTumorModel -> log prediction -> return result

        brain_model = self.models.get_brain_model()
        model_result = brain_model.predict(image_path)
        
        predicted_class: str = model_result.get("predicted_class", "unknown")
        probability: float = float(model_result.get("probability", 0.0))
        probabilities: Dict[str, float] = model_result.get("probabilities", {})
        
        # Decide if this is considered "tumor" or "no_tumor"
        tumor_classes = {"glioma", "meningioma", "pituitary"}
        is_tumor = predicted_class in tumor_classes
        
        # Build a short input summary for logging
        input_summary = f"image_path={image_path.name if hasattr(image_path, 'name') else str(image_path)}"

        # --------------------
        # Log prediction in DB + get log_id
        # --------------------
        log_id: Optional[int] = None

        if user_id is not None:
            # Insert log and get the inserted row ID in the same transaction
            log_id = self.db.execute_and_get_id(
                """
                INSERT INTO prediction_logs (
                    user_id, model_type, input_summary,
                    prediction_result, probability, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "brain_tumor_multiclass",
                    input_summary,
                    predicted_class,
                    probability,
                    self._now_iso(),
                ),
            )

        # Build a user-friendly suggestion message
        suggestion = self._generate_brain_suggestion(predicted_class, is_tumor, probability)

        return {
            "predicted_class": predicted_class,
            "probability": probability,
            "probabilities": probabilities,
            "is_tumor": is_tumor,
            "input_summary": input_summary,
            "suggestion": suggestion,
            "log_id": log_id,
        }

    def _generate_brain_suggestion(
        self,
        predicted_class: str,
        is_tumor: bool,
        probability: float,
    ) -> str:

        prob_pct = round(probability * 100)

        if predicted_class == "no_tumor":
            return (
                f"The model's highest confidence class is 'no_tumor' "
                f"with an estimated probability of about {prob_pct}%. "
                "This does not guarantee that no abnormality exists. "
                "If you have any symptoms or concerns, please consult a neurologist or radiologist."
            )

        # tumor classes
        base_msg = (
            f"The model suggests the MRI is most consistent with '{predicted_class}' "
            f"with an estimated probability of about {prob_pct}%. "
            "This is NOT a clinical diagnosis."
        )

        follow_up = (
            "You should promptly consult a qualified neurologist or neurosurgeon, "
            "and have this MRI evaluated by a radiologist for a professional interpretation."
        )

        return base_msg + " " + follow_up
    
# Global instance used by routes
prediction_service = PredictionService()
