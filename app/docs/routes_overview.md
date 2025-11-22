# Multi Disease Detection System – Routes Overview

This document describes all Flask routes (URLs), which HTML templates they use,
and which backend services / models they depend on.

---

## 1. Public Routes (No Login Required)

These routes can be accessed by anyone.

| URL Path   | Methods   | Template (in `app/ui/pages`) | Main Service / Logic                        | Description                                      |
|-----------|-----------|-------------------------------|---------------------------------------------|--------------------------------------------------|
| `/`       | GET       | `welcome.html`               | – (no heavy logic)                          | Landing page with app name + “Get Started”.      |
| `/login`  | GET, POST | `login.html`                 | `AuthService` (`services/authentication/`)  | Show login form (GET) and process login (POST).  |
| `/register` | GET, POST | `register.html`            | `AuthService` (`services/authentication/`)  | Show register form (GET) and create account (POST). |

**Notes**

- `AuthService` uses:
  - `User` model (`models/user/user.py`)
  - `DatabaseManager` (`core/managers/database_manager.py`)

---

## 2. Auth-Protected Routes (Login Required)

These routes require the user to be logged in (later: session check).

| URL Path        | Methods   | Template (in `app/ui/pages`)  | Main Service / Logic                            | Description                                                    |
|-----------------|-----------|--------------------------------|-------------------------------------------------|----------------------------------------------------------------|
| `/dashboard`    | GET       | `dashboard.html`              | – (light logic; may use small helper functions) | Main hub after login; shows cards for features.                |
| `/brain-tumor`  | GET, POST | `brain_tumor.html`            | `PredictionService` (`services/prediction/`)    | Upload MRI image (GET), run CNN prediction (POST).             |
| `/heart-disease`| GET, POST | `heart_disease.html`          | `PredictionService` (`services/prediction/`)    | Show heart form (GET), run RF prediction (POST).               |
| `/chatbot`      | GET, POST | `chatbot.html`                | `ChatbotService` (`services/chatbot/`)          | Show chat UI (GET), send/receive messages to API (POST/AJAX).  |
| `/settings`     | GET, POST | `settings.html`               | `AuthService` (+ optional settings service)     | Show settings (GET), change password/theme (POST).             |

**Notes**

- `PredictionService` talks to:
  - `ModelManager` (`core/managers/model_manager.py`)
  - `HeartDiseaseModel` (`models/heart/heart_disease_model.py`)
  - `BrainTumorModel` (`models/brain/brain_tumor_model.py`)
- `ChatbotService` talks to:
  - External chatbot API (e.g., OpenAI / Groq etc., to be chosen later).

---

## 3. Utility Routes

Helper routes for logout and generic error handling.

| URL Path | Methods | Template (in `app/ui/pages`) | Main Service / Logic                       | Description                                |
|----------|---------|-------------------------------|--------------------------------------------|--------------------------------------------|
| `/logout`| GET     | – (redirect only)            | `AuthService` (`logout` helper)            | Clears session and redirects to `/`.       |
| `/error` | GET     | `error_generic.html`         | – (may log error via a utility/logger)     | Generic error page for unexpected problems.|

---

## 4. High-Level Flow – Heart Disease Detection

1. **Browser** requests **`GET /heart-disease`**  
   → Flask route in `app/routes.py`  
   → Renders `heart_disease.html` (form).

2. User fills the form and submits → **`POST /heart-disease`**  
   - Route collects form data into a dictionary.
   - Route calls `PredictionService.predict_heart_disease(form_data)`.

3. `PredictionService`:
   - Requests a model from `ModelManager.get_heart_model()`.
   - `ModelManager` loads (or reuses) `HeartDiseaseModel` from `data/saved_models/`.
   - `HeartDiseaseModel.predict(features_dict)` returns:
     - Prediction (e.g., 0/1 or “Low/Medium/High risk”).
     - Probability or confidence.

4. Route receives the result and passes it to `heart_disease.html` for display.

**Chain summary**

`Browser → /heart-disease route → PredictionService → ModelManager → HeartDiseaseModel → back to route → Browser`

---

## 5. High-Level Flow – Brain Tumor Detection

1. **Browser** requests **`GET /brain-tumor`**  
   → Route renders `brain_tumor.html` with file upload form.

2. User uploads MRI image → **`POST /brain-tumor`**  
   - Route saves file via helper in `ui`/`utils` (later).
   - Route calls `PredictionService.predict_brain_tumor(image_path)`.

3. `PredictionService`:
   - Gets CNN model via `ModelManager.get_brain_model()`.
   - `BrainTumorModel.predict(image)` returns:
     - Tumor / no tumor.
     - Tumor type (optional: meningioma/glioma/pituitary).
     - Confidence score.

4. Route passes results to `brain_tumor.html` and displays them.

**Chain summary**

`Browser → /brain-tumor route → PredictionService → ModelManager → BrainTumorModel → back to route → Browser`

---

## 6. High-Level Flow – AI Doctor Chatbot

1. **GET /chatbot**
   - Route renders `chatbot.html` with basic chat layout.

2. User sends a message:
   - Either via standard **form POST** to `/chatbot`,
   - Or via **AJAX** call (later decision).

3. Route calls `ChatbotService.send_message(user_message)`.

4. `ChatbotService`:
   - Builds a request with:
     - System prompt: “You are a professional medical assistant…”
     - User’s message.
   - Sends it to the external chatbot API.
   - Receives and returns the reply text.

5. Route sends the reply back to the browser; `chatbot.html` displays it in the chat history.

**Chain summary**

`Browser → /chatbot route → ChatbotService → External API → ChatbotService → route → Browser`

---

## 7. Route Ownership (Where they are defined)

- All route functions (`@app.route(...)`) will be defined in **`app/routes.py`**.
- Each route will be kept **thin**, delegating work to:
  - `AuthService`
  - `PredictionService`
  - `ChatbotService`
  - `DatabaseManager`
  - `ModelManager`
  - Domain models (`User`, `HeartDiseaseModel`, `BrainTumorModel`)

This ensures a clean separation between:
- **Routing / HTTP layer** (in `routes.py`)
- **Business logic** (in `services/`)
- **Data access / model loading** (in `core/managers/` and `models/`).
