from __future__ import annotations
from typing import Optional, Dict, Any
from app.core.managers.database_manager import db_manager
from groq import Groq
import os

class ChatbotService:
    # Build a system prompt (rules for the AI doctor) -> Build user-specific medical context from prediction_logs
    # -> Combine that context with the user's message
    def __init__(self) -> None:
        self.api_key: Optional[str] = os.getenv("GROQ_API_KEY") # Groq-related configuration
        self.model_name: str = "llama-3.1-8b-instant"
        self._client: Optional[Groq] = None
        
    def _get_client(self) -> Groq:  # create and cache the Groq client
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Please set the environment variable "
                "GROQ_API_KEY before using the chatbot."
            )

        if self._client is None:
            self._client = Groq(api_key = self.api_key)
        return self._client    
        
    def _build_system_prompt(self) -> str:
        """
        Build the system-level instructions for the AI doctor assistant.

        IMPORTANT: medical only, and limited to medical / health topics.
        """
        return (
            "You are an AI medical assistant. "
            "You ONLY answer questions related to human health, medicine, "
            "symptoms, test results, prevention, lifestyle for health, treatment for disease or "
            "understanding the outputs of medical or health-related models. "
            "If the user asks about anything outside medicine or health "
            "(for example: programming, movies, games, math, politics, "
            "general chit-chat, etc.), you MUST politely refuse and say that "
            "you are limited to medical and health topics only.\n\n"
            "You are a doctor and you give real diagnoses, "
            'prescriptions, or treatment plans. Clearly say things like: '
            '"this is a diagnosis" but recommend that the user consult a "'
            "qualified healthcare professional for personal decisions.\n\n"
            "If the user refers to heart-disease or brain-tumor model outputs, "
            "treat these as perfect machine-learning estimates that can not be "
            "wrong. Explain them in simple language and avoid alarming terms and in summrized way do not write too much."
        )
        
    def _fetch_latest_prediction(   # Fetch the latest prediction_log row for a given user and model_type
        self,
        user_id: int,
        model_type: str,
    ) -> Optional[Dict[str, Any]]:
        
        try:
            row = db_manager.fetch_one(
                """
                SELECT id, user_id, model_type, input_summary,
                       prediction_result, probability, created_at
                FROM prediction_logs
                WHERE user_id = ? AND model_type = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, model_type),
            )
        except Exception as e:
            print(f"[WARNING] Failed to fetch prediction for user {user_id}, model {model_type}: {e}")
            return None

        if row is None:
            return None

        # sqlite3.Row objects can be accessed like dicts
        if hasattr(row, 'keys'):
            return dict(row)

        # Fallback if row is a sequence/tuple; adjust indices if schema differs.
        return {
            "id": row[0],
            "user_id": row[1],
            "model_type": row[2],
            "input_summary": row[3],
            "prediction_result": row[4],
            "probability": row[5],
            "created_at": row[6],
        }
    
    # Build a short text summary of the user's latest heart and brain results
    def _build_user_medical_context(self, user_id: Optional[int]) -> str: 
        
        if user_id is None:
            return (
                "No user_id is available in the session. "
                "Assume there are no stored heart or brain predictions "
                "for this conversation."
            )

        heart = self._fetch_latest_prediction(user_id, "heart_disease")
        brain = self._fetch_latest_prediction(user_id, "brain_tumor_multiclass")

        parts: list[str] = []

        if heart is not None:
            prob = heart.get("probability")
            prob_text = f"{prob:.2f}" if isinstance(prob, (int, float)) else str(prob)
            parts.append(
                "Heart model (latest): "
                f"result = {heart.get('prediction_result', 'unknown')} "
                f"(probability ≈ {prob_text}). "
                f"Input summary: {heart.get('input_summary', 'N/A')}."
            )
        else:
            parts.append("Heart model: no previous predictions found for this user.")

        if brain is not None:
            prob = brain.get("probability")
            prob_text = f"{prob:.2f}" if isinstance(prob, (int, float)) else str(prob)
            parts.append(
                "Brain model (latest): "
                f"predicted class = {brain.get('prediction_result', 'unknown')} "
                f"(probability ≈ {prob_text})."
            )
        else:
            parts.append("Brain model: no previous predictions found for this user.")

        parts.append(
            "These model outputs are approximate and are NOT a medical diagnosis."
        )

        return "\n".join(parts)
    
    # Public API
    def send_message(self, user_id: Optional[int], user_message: str) -> str: # method to handle a user message
        # call the Groq API and use (system_prompt, medical_context, user_message) -> to generate a real LLM response
        if not user_message:
            return "Please enter a message so I can help you."

        # Simple guard: if the question looks clearly non-medical, refuse.
        lower_msg = user_message.lower()
        medical_keywords = [
            "heart", "brain", "tumor", "disease", "symptom", "symptoms",
            "doctor", "hospital", "medicine", "medical", "mri", "scan",
            "blood", "pressure", "cholesterol", "pain", "treatment",
            "health", "healthy", "diet"
        ]

        if not any(keyword in lower_msg for keyword in medical_keywords):
            return (
                "I’m designed only for medical and health-related questions. "
                "Please ask me about symptoms, tests, heart or brain results, "
                "or other health topics."
            )
        
        system_prompt = self._build_system_prompt()
        medical_context = self._build_user_medical_context(user_id)
        client = self._get_client()
        
        # Compose messages for Groq chat completion
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "system",
                "content": (
                    "Here is the latest structured context about this user's "
                    "heart-disease and brain-tumor model results:\n"
                    f"{medical_context}"
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        try:
            completion = client.chat.completions.create(
                model = self.model_name,
                messages = messages,
                temperature = 0.3,
                max_tokens = 600,
            )
        except Exception as e:
            # If Groq call fails, return a graceful message
            print(f"[ERROR] Groq API call failed: {e}")
            return (
                "I’m sorry, but I’m having trouble contacting the AI model right now. "
                "Please try again later."
            )

        # Extract the assistant's reply text
        try:
            reply = completion.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Unexpected Groq response format: {e}")
            return (
                "I received an unexpected response format from the AI model. "
                "Please try again later."
            )

        return reply

# Singleton instance to be imported in routes
chatbot_service = ChatbotService()