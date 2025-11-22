# Multi Disease Detection System – OOP Design

This document lists the main classes in the backend, where they live, their
attributes, main methods (names only), and the OOP concepts they use.

---

## 1. Domain Model: `User`

**Class name:** `User`  
**File path:** `app/models/user/user.py`

**Attributes (conceptual):**
- `id`
- `username`
- `email`
- `password_hash`
- `created_at`
- `updated_at`
- `is_active`

**Methods (names only):**
- `set_password(plain_password)`
- `check_password(plain_password) -> bool`
- `to_dict()`

**OOP concepts used:**
- **Encapsulation:** password hashing/checking is hidden inside the class.
- **Abstraction:** other layers only call methods (no direct handling of hashes).

---

## 2. Base ML Model: `DetectionModel`

**Class name:** `DetectionModel` (abstract/base class)  
**File path:** `app/core/base/base_model.py`

**Attributes:**
- `name`
- `model_path`
- `loaded_model`

**Methods:**
- `load_model()`
- `predict(input_data)`  *(abstract – implemented by subclasses)*
- `preprocess(raw_input)` *(optional, can be abstract or default)*

**OOP concepts used:**
- **Abstraction:** defines common interface for all detection models.
- **Inheritance:** concrete models derive from this base.
- **Polymorphism:** different models implement `predict()` differently.

---

## 3. Heart Disease Model: `HeartDiseaseModel`

**Class name:** `HeartDiseaseModel`  
**File path:** `app/models/heart/heart_disease_model.py`

**Attributes:**
- Inherits from `DetectionModel`:
  - `name = "Heart Disease Model"`
  - `model_path` (path to RF `.pkl` file)
  - `loaded_model`

**Methods:**
- `load_model()`
- `predict(features_dict) -> (label, probability)`
- `preprocess(features_dict)` *(if needed)*

**OOP concepts used:**
- **Inheritance:** extends `DetectionModel`.
- **Polymorphism:** its `predict()` is specific to Random Forest.
- **Encapsulation:** hides details of preprocessing and RF calls.

---

## 4. Brain Tumor Model: `BrainTumorModel`

**Class name:** `BrainTumorModel`  
**File path:** `app/models/brain/brain_tumor_model.py`

**Attributes:**
- Inherits from `DetectionModel`:
  - `name = "Brain Tumor Model"`
  - `model_path` (path to CNN `.h5` or similar)
  - `loaded_model`

**Methods:**
- `load_model()`
- `preprocess(image_path_or_file)`
- `predict(image_path_or_file) -> (label, probability)`

**OOP concepts used:**
- **Inheritance:** extends `DetectionModel`.
- **Polymorphism:** own `predict()` implementation using CNN.
- **Encapsulation:** hides image loading, preprocessing, and model details.

---

## 5. Database Manager: `DatabaseManager`

**Class name:** `DatabaseManager`  
**File path:** `app/core/managers/database_manager.py`

**Attributes:**
- `db_path` (path to `instance/app.db`)
- (optionally) internal connection management fields

**Methods:**
- `get_connection()`
- `execute(query, params=())`
- `fetch_one(query, params=())`
- `fetch_all(query, params=())`
- (optional) `init_db()`

**OOP concepts used:**
- **Encapsulation:** hides SQLite connection + query details.
- **Single Responsibility:** only handles DB operations.

---

## 6. Model Manager: `ModelManager`

**Class name:** `ModelManager`  
**File path:** `app/core/managers/model_manager.py`

**Attributes:**
- `heart_model` (instance of `HeartDiseaseModel` or `None`)
- `brain_model` (instance of `BrainTumorModel` or `None`)

**Methods:**
- `get_heart_model() -> HeartDiseaseModel`
- `get_brain_model() -> BrainTumorModel`

**OOP concepts used:**
- **Encapsulation:** controls when/how models are loaded and cached.
- **(Singleton-like behavior):** ensures one instance per model in the app.

---

## 7. Authentication Service: `AuthService`

**Class name:** `AuthService`  
**File path:** `app/services/authentication/auth_service.py`

**Attributes:**
- Reference to `DatabaseManager`
- (optionally) config/settings

**Methods:**
- `register(username, email, password) -> (success, message)`
- `login(identifier, password) -> (success, user_or_message)`
- `change_password(user_id, old_password, new_password) -> (success, message)`

**OOP concepts used:**
- **Encapsulation:** hides all registration/login details from routes.
- **Separation of Concerns:** keeps auth logic out of HTTP layer.

---

## 8. Prediction Service: `PredictionService`

**Class name:** `PredictionService`  
**File path:** `app/services/prediction/prediction_service.py`

**Attributes:**
- Reference to `ModelManager`
- Reference to `DatabaseManager`

**Methods:**
- `predict_heart_disease(form_data) -> dict`
- `predict_brain_tumor(image_file) -> dict`

*(Each returns a dict with label, probability, and maybe suggestion text.)*

**OOP concepts used:**
- **Polymorphism:** uses different models via common `DetectionModel` interface.
- **Encapsulation:** routes don’t know about preprocessing, logging, or model loading.

---

## 9. Chatbot Service: `ChatbotService`

**Class name:** `ChatbotService`  
**File path:** `app/services/chatbot/chatbot_service.py`

**Attributes:**
- API configuration (API key, base URL, model name, etc.)
- Reference to `DatabaseManager` (for chat_logs)

**Methods:**
- `send_message(user_id, user_message) -> assistant_reply`
- `get_recent_messages(user_id, limit=20)` *(optional)*

**OOP concepts used:**
- **Encapsulation:** hides HTTP/API details from routes.
- **Abstraction:** if the API provider changes, only this class changes.

---

## 10. (Optional) Base Service: `BaseService`

**Class name:** `BaseService`  
**File path:** `app/core/base/base_service.py`

**Attributes:**
- (optional) shared logger
- (optional) reference to `DatabaseManager`

**Methods:**
- (optional) common helper methods for error handling/logging

**OOP concepts used:**
- **Inheritance:** `AuthService`, `PredictionService`, `ChatbotService` can extend this.
- **Abstraction:** defines shared behavior for all services.

---

## 11. (Optional) Base Controller: `BaseController`

**Class name:** `BaseController`  
**File path:** `app/core/base/base_controller.py`

**Attributes:**
- (optional) references to common services

**Methods:**
- (optional) helper methods for controllers/routes

**OOP concepts used:**
- **Abstraction / Inheritance:** possible parent class for more structured controllers later.

---
