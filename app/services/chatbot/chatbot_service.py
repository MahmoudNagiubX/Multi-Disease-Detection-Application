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
        Responses must be concise and summarized.
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
            
            "RESPONSE STYLE - BE CONCISE AND SUMMARIZED:\n"
            "- Answer in a concise, summarized way. Avoid long essays or walls of text.\n"
            "- Use short paragraphs (1-3 lines each) and bullet points when appropriate.\n"
            "- Keep most answers within roughly 5-10 short bullet points or 3-6 short paragraphs.\n"
            "- Prioritize clarity and key points over excessive detail.\n"
            "- Do NOT repeat the same information multiple times.\n"
            "- Do NOT over-explain simple things.\n"
            "- Write only what is necessary to answer the question clearly and safely.\n\n"
            
            "MEDICAL SAFETY RULES:\n"
            "You are a doctor and you give real diagnoses, "
            'prescriptions, or treatment plans. Clearly say things like: '
            '"this is a diagnosis" but recommend that the user consult a "'
            "qualified healthcare professional for personal decisions.\n\n"
            
            "If the user refers to heart-disease or brain-tumor model outputs, "
            "treat these as perfect machine-learning estimates that can not be "
            "wrong. Explain them in simple language, avoid alarming terms, "
            "and keep explanations brief and summarized."
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
                "content": f"{user_message}\n\nPlease answer briefly and concisely.",
            },
        ]

        try:
            completion = client.chat.completions.create(
                model = self.model_name,
                messages = messages,
                temperature = 0.3,
                max_tokens = 500,  # Reduced for more concise responses
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
    
    def _build_symptom_analysis_system_prompt(self) -> str:
        """
        Build the system prompt for symptom analysis mode.
        This implements a "doctor with memory" - a medical assistant that remembers
        the user's past AI test results and connects them to current symptoms.
        Returns concise, structured, organized responses.
        """
        return (
            "You are a medical triage assistant acting as a family doctor with access to "
            "the patient's medical history. You have their latest AI test results from "
            "heart disease and brain tumor screenings. Your role is to analyze their "
            "current symptoms in the context of their medical history.\n\n"
            
            "CORE BEHAVIOR:\n"
            "1. Recall their past AI test results (heart disease risk, brain tumor patterns)\n"
            "2. Look for connections between current symptoms and past results\n"
            "3. Provide specific, relevant advice based on their complete picture\n\n"
            
            "REQUIRED OUTPUT STRUCTURE - ORGANIZED AND STRUCTURED:\n"
            "Format your response EXACTLY as follows with clear headings and bullet points:\n\n"
            
            "**Possible Causes (Not a Diagnosis)**\n"
            "- Use 2-4 bullet points maximum\n"
            "- Each bullet: 1-2 lines, use cautious language ('may be', 'could be', 'might indicate')\n"
            "- List potential systems/conditions that could explain symptoms\n\n"
            
            "**When to See a Doctor**\n"
            "- Use 2-4 bullet points maximum\n"
            "- Each bullet: 1-2 lines\n"
            "- Clearly state urgency: ER visit needed vs. schedule appointment vs. monitor\n"
            "- Highlight emergency red flags (chest pain, severe headache, etc.)\n\n"
            
            "**What to Avoid & Lifestyle Tips**\n"
            "- Use 2-4 bullet points maximum\n"
            "- Each bullet: 1-2 lines\n"
            "- Provide safe, general home-care tips\n"
            "- Suggest lifestyle changes if relevant\n\n"
            
            "**How Your AI Results Fit In**\n"
            "- Use 2-3 bullet points maximum\n"
            "- Each bullet: 1-2 lines\n"
            "- Explain how heart/brain AI results might relate to symptoms\n"
            "- Use cautious language - these are estimates, not diagnoses\n\n"
            
            "**Treatment for Heart/Brain AI Results** (only if AI results are relevant)\n"
            "- Use 2-3 bullet points maximum\n"
            "- Each bullet: 1-2 lines\n"
            "- Provide general guidance, not specific prescriptions\n"
            "- Emphasize consulting healthcare professional\n\n"
            
            "**Educational Explanation**\n"
            "- Use 1-2 short paragraphs (1-3 lines each)\n"
            "- Briefly explain what might be happening in the body\n"
            "- Keep it simple and educational\n\n"
            
            "**Important Disclaimer**\n"
            "- Use 1-2 short sentences\n"
            "- Remind that this is educational, not a clinical diagnosis\n"
            "- Emphasize consulting a qualified healthcare professional\n\n"
            
            "STRICT CONCISENESS REQUIREMENTS:\n"
            "- Answer in a concise, summarized format. NO long essays or walls of text.\n"
            "- Each section: Maximum 2-4 bullet points OR 1-3 short paragraphs (1-3 lines each).\n"
            "- Total response length: Aim for 15-25 lines total (excluding section headers).\n"
            "- Use bullet points for lists - they are easier to scan.\n"
            "- Use short paragraphs (1-3 lines) when bullets aren't appropriate.\n"
            "- Focus ONLY on the most important points - prioritize clarity over detail.\n"
            "- Do NOT repeat information across sections.\n"
            "- Do NOT over-explain simple concepts.\n"
            "- Write only what is necessary to answer clearly and safely.\n"
            "- Make the response compact, organized, and easy to scan.\n\n"
            
            "ORGANIZATION REQUIREMENTS:\n"
            "- Use clear, bold section headings (exactly as specified above).\n"
            "- Maintain consistent formatting throughout.\n"
            "- Use bullet points (-) for lists within sections.\n"
            "- Keep sections in the exact order specified.\n"
            "- Ensure each section is visually distinct and easy to find.\n\n"
            
            "CRITICAL SAFETY RULES:\n"
            "- You MUST use cautious language ('may be', 'could be', 'might indicate').\n"
            "- You MUST emphasize visiting a real doctor for serious symptoms.\n"
            "- You MUST highlight emergency red flags clearly.\n"
            "- You MUST NOT give final medical diagnoses.\n"
            "- You MUST NOT prescribe medications, doses, or specific treatments.\n"
            "- You MUST NOT confirm diseases definitively.\n"
            "- You MUST treat AI model results as approximate estimates, not diagnoses.\n"
            "- You MUST provide educational information only.\n"
            "- You MUST connect symptoms to patient's AI results when relevant.\n\n"
            
            "Remember: You are a medical assistant with memory of the patient's test results. "
            "Provide concise, structured, organized advice that is easy to read and understand."
        )
    
    def _build_symptom_analysis_context(self, user_id: Optional[int]) -> str:
        """
        Build a detailed context string for symptom analysis using latest heart and brain predictions.
        This creates a "medical file" that the AI doctor can review, just like a real doctor
        would check a patient's chart before diagnosing.
        """
        if user_id is None:
            return (
                "PATIENT MEDICAL FILE:\n"
                "No user_id available. This patient has no stored AI test results in their file.\n"
                "Proceed with symptom analysis without historical context."
            )
        
        heart = self._fetch_latest_prediction(user_id, "heart_disease")
        brain = self._fetch_latest_prediction(user_id, "brain_tumor_multiclass")
        
        parts: list[str] = [
            "═══════════════════════════════════════════════════════════",
            "PATIENT MEDICAL FILE - AI TEST RESULTS HISTORY",
            "═══════════════════════════════════════════════════════════",
            ""
        ]
        
        if heart is not None:
            prob = heart.get("probability")
            prob_pct = f"{float(prob) * 100:.1f}%" if isinstance(prob, (int, float)) else str(prob)
            created_at = heart.get("created_at", "unknown date")
            result = heart.get("prediction_result", "unknown")
            parts.append(
                f"HEART DISEASE SCREENING:\n"
                f"  Result: {result} risk level\n"
                f"  Probability: {prob_pct}\n"
                f"  Date: {created_at}\n"
            )
        else:
            parts.append(
                "HEART DISEASE SCREENING:\n"
                "  Status: No previous heart disease predictions found in patient file.\n"
            )
        
        parts.append("")  # Blank line
        
        if brain is not None:
            prob = brain.get("probability")
            prob_pct = f"{float(prob) * 100:.1f}%" if isinstance(prob, (int, float)) else str(prob)
            created_at = brain.get("created_at", "unknown date")
            result = brain.get("prediction_result", "unknown")
            parts.append(
                f"BRAIN MRI SCREENING:\n"
                f"  Result: {result} pattern detected\n"
                f"  Probability: {prob_pct}\n"
                f"  Date: {created_at}\n"
            )
        else:
            parts.append(
                "BRAIN MRI SCREENING:\n"
                "  Status: No previous brain tumor predictions found in patient file.\n"
            )
        
        parts.extend([
            "",
            "═══════════════════════════════════════════════════════════",
            "IMPORTANT: These AI predictions are approximate estimates",
            "and are NOT medical diagnoses. They are educational context",
            "only. Use them to inform your analysis, but do not treat",
            "them as confirmed diagnoses.",
            "═══════════════════════════════════════════════════════════",
            "",
            "INSTRUCTIONS: Review this patient's file before analyzing their symptoms. "
            "Look for connections between their current symptoms and these past test results. "
            "For example: If they report dizziness and their file shows a brain tumor pattern "
            "from last week, consider if there might be a connection. If they report chest pain "
            "and their file shows high heart disease risk from yesterday, consider cardiovascular causes."
        ])
        
        return "\n".join(parts)
    
    def analyze_symptoms(self, symptom_text: str, user_id: Optional[int]) -> str:
        """
        Analyze symptoms using LLM with user's latest heart/brain AI results as context.
        
        Args:
            symptom_text: Free-text description of symptoms
            user_id: Optional user ID to fetch latest predictions
            
        Returns:
            Structured educational medical analysis as a string
            
        Raises:
            RuntimeError: If GROQ_API_KEY is missing or API call fails
        """
        # Validate input
        if not symptom_text or len(symptom_text.strip()) < 10:
            return (
                "Please provide a more detailed description of your symptoms "
                "(at least 10 characters). For example: 'I have been experiencing "
                "chest pain and shortness of breath for the past week.'"
            )
        
        symptom_text = symptom_text.strip()
        
        # Build context from user's latest predictions
        ai_context = self._build_symptom_analysis_context(user_id)
        
        # Get Groq client
        try:
            client = self._get_client()
        except RuntimeError as e:
            if "GROQ_API_KEY" in str(e):
                return (
                    "Symptom checker is currently unavailable due to configuration issues. "
                    "Please contact support or try again later."
                )
            raise
        
        # Build system prompt for symptom analysis
        system_prompt = self._build_symptom_analysis_system_prompt()
        
        # Compose messages for Groq chat completion
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "system",
                "content": (
                    "Here is the user's latest AI model results for context:\n"
                    f"{ai_context}\n\n"
                    "Use this information to provide relevant analysis, but remember "
                    "these are approximate estimates, not diagnoses."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyze these symptoms and provide a structured medical analysis. "
                    f"Keep your response concise, organized, and summarized. "
                    f"Use the exact section structure with 2-4 bullet points per section. "
                    f"Each bullet should be 1-2 lines. Avoid long explanations.\n\n"
                    f"Symptoms: {symptom_text}"
                ),
            },
        ]
        
        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.4,  # Slightly higher for more nuanced analysis
                max_tokens=800,  # Reduced for more concise responses while keeping structure
            )
        except Exception as e:
            print(f"[ERROR] Groq API call failed in analyze_symptoms: {e}")
            return (
                "I'm sorry, but I'm having trouble analyzing your symptoms right now. "
                "Please try again later or consult a qualified healthcare professional."
            )
        
        # Extract the assistant's reply text
        try:
            reply = completion.choices[0].message.content
            if not reply:
                return (
                    "I received an empty response from the AI model. "
                    "Please try again or consult a healthcare professional."
                )
            return reply
        except Exception as e:
            print(f"[ERROR] Unexpected Groq response format in analyze_symptoms: {e}")
            return (
                "I received an unexpected response format from the AI model. "
                "Please try again later or consult a qualified healthcare professional."
            )

# Singleton instance to be imported in routes
chatbot_service = ChatbotService()