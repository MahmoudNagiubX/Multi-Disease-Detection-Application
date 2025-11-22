from typing import Optional
from app.models.heart.heart_disease_model import HeartDiseaseModel
from app.models.brain.brain_tumor_model import BrainTumorModel

class ModelManager: # Manages ML/DL model instances
    def __init__(self) -> None:
        self._heart_model: Optional[HeartDiseaseModel] = None
        self._brain_model = None 
        
    def get_heart_model(self) -> HeartDiseaseModel: #  Return a loaded HeartDiseaseModel instance
        if self._heart_model is None:
            # In the future we may pass a real model_path here.
            self._heart_model = HeartDiseaseModel(
                model_path="app/data/saved_models/heart_model.pkl"
            )
            self._heart_model.load_model()
        return self._heart_model

    def get_brain_model(self) -> BrainTumorModel:   # Return a loaded BrainTumorModel instance
        if self._brain_model is None:
            # Model will use default path or can be overridden
            # The model loads lazily when predict() is first called
            self._brain_model = BrainTumorModel()
        return self._brain_model

# Global instance used by services
model_manager = ModelManager()