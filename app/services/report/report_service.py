from __future__ import annotations
from typing import Optional, Dict, Any
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from app.core.managers.database_manager import db_manager
from app.models.user.user import User


class ReportService:
    """
    Handles creation of PDF reports for predictions.
    - Fetches prediction_log rows for a given user
    - Generates PDF reports for heart disease predictions
    - Generates PDF reports for brain tumor predictions
    """
    
    def _row_to_log_dict(self, row) -> Dict[str, Any]:
        """
        Convert a DB row into a plain dict.
        Expected columns:
            id, user_id, model_type, input_summary,
            prediction_result, probability, created_at
        """
        if hasattr(row, "keys"):
            # sqlite3.Row or dict-like
            return dict(row)

        # tuple fallback
        return {
            "id": row[0],
            "user_id": row[1],
            "model_type": row[2],
            "input_summary": row[3],
            "prediction_result": row[4],
            "probability": row[5],
            "created_at": row[6],
        }

    def get_prediction_for_user(
        self,
        log_id: int,
        user_id: int,
        model_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a prediction_logs row by id + user_id,
        optionally filtered by model_type.
        """
        params = [log_id, user_id]
        query = """
            SELECT id, user_id, model_type, input_summary,
                   prediction_result, probability, created_at
            FROM prediction_logs
            WHERE id = ? AND user_id = ?
        """

        if model_type:
            query += " AND model_type = ?"
            params.append(model_type)

        row = db_manager.fetch_one(query, tuple(params))
        if row is None:
            return None

        return self._row_to_log_dict(row)

    # ------------------------------------------------------------------
    # Helpers for formatting
    # ------------------------------------------------------------------
    def _format_datetime(self, value: Any) -> str:
        """
        Try to format ISO datetime string nicely as 'YYYY-MM-DD HH:MM'.
        """
        if not value:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        try:
            dt = datetime.fromisoformat(str(value))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(value)

    def _probability_to_percent(self, prob: Any) -> str:
        """
        Convert stored probability to '87%' style string.
        """
        try:
            p = float(prob)
            return f"{p * 100:.1f}%"
        except Exception:
            return str(prob)

    def _heart_risk_explanation(self, risk_label: str) -> str:
        """
        A short text similar to PredictionService._generate_heart_suggestion,
        but tailored for the PDF report.
        """
        if risk_label == "High":
            return (
                "The model estimated a HIGH risk of heart disease based on the "
                "provided features. This is not a diagnosis. You should "
                "strongly consider seeing a cardiologist for full medical tests."
            )
        elif risk_label == "Medium":
            return (
                "The model estimated a MEDIUM risk of heart disease. It may be "
                "helpful to monitor your blood pressure, cholesterol, and "
                "discuss lifestyle changes and screening with a healthcare "
                "professional."
            )
        else:
            return (
                "The model estimated a LOW risk of heart disease. Maintaining a "
                "healthy lifestyle, exercising regularly, and having periodic "
                "check-ups is still important."
            )

    def _brain_class_explanation(self, predicted_class: str) -> str:
        """
        Provide a simple textual explanation for a brain tumor class.
        """
        cls = (predicted_class or "").lower().strip()
        if cls == "no_tumor":
            return (
                "The model did not detect a brain tumor pattern in the MRI image. "
                "However, this is only an AI model output and cannot replace a "
                "radiologist's professional interpretation."
            )
        elif cls == "glioma":
            return (
                "The model pattern is most consistent with a glioma-type tumor. "
                "This does NOT confirm a diagnosis. A radiologist and "
                "neurospecialist must review the MRI and perform full clinical "
                "evaluation."
            )
        elif cls == "meningioma":
            return (
                "The model pattern is most consistent with a meningioma-type tumor. "
                "This is only an AI pattern suggestion and not a diagnosis. "
                "A specialist must confirm any findings."
            )
        elif cls == "pituitary":
            return (
                "The model pattern is most consistent with a pituitary-region tumor. "
                "This is not a confirmed diagnosis. A radiologist and doctor must "
                "interpret the MRI and clinical picture."
            )
        else:
            return (
                "The model could not clearly map the MRI to one of the expected "
                "classes, or the class name is unknown. Only a qualified doctor "
                "and radiologist can interpret the scan reliably."
            )

    def _medical_disclaimer(self) -> str:
        """
        Common disclaimer added to all reports.
        """
        return (
            "This report is generated by an AI-based educational system. All "
            "results are approximate and can be wrong. This is NOT a medical "
            "diagnosis, prescription, or a substitute for professional medical "
            "advice. Always consult a qualified doctor or healthcare provider "
            "for any decisions about your health."
        )

    # ------------------------------------------------------------------
    # PDF generation helpers
    # ------------------------------------------------------------------
    def _create_canvas(self) -> canvas.Canvas:
        """
        Create a ReportLab canvas on a BytesIO buffer and return the canvas.
        The caller is responsible for saving and rewinding the buffer.
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        # Attach buffer to canvas so caller can access it later
        c._buffer = buffer  # type: ignore[attr-defined]
        return c

    def _finish_canvas(self, c: canvas.Canvas) -> BytesIO:
        """
        Finalize the PDF and return the BytesIO buffer.
        """
        c.showPage()
        c.save()
        buffer: BytesIO = c._buffer  # type: ignore[assignment]
        buffer.seek(0)
        return buffer

    # ------------------------------------------------------------------
    # Public API: Generate heart report
    # ------------------------------------------------------------------
    def generate_heart_report(self, user: User, log: Dict[str, Any]) -> BytesIO:
        """
        Create a PDF report for a heart-disease prediction.
        """
        c = self._create_canvas()
        width, height = A4

        # Margins
        margin_left = 20 * mm
        margin_top = height - 20 * mm

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin_left, margin_top, "Heart Disease Risk Report")

        # Subtitle
        c.setFont("Helvetica", 10)
        c.drawString(
            margin_left,
            margin_top - 14,
            "Multi Disease Detection System – Educational AI output",
        )

        # Section: Patient info
        y = margin_top - 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_left, y, "Patient information")

        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(margin_left, y, f"Name: {user.username}")
        y -= 14
        c.drawString(margin_left, y, f"Email: {user.email or 'N/A'}")
        y -= 14
        c.drawString(
            margin_left,
            y,
            f"Report generated from log ID: {log.get('id')} "
            f"on {self._format_datetime(log.get('created_at'))}",
        )

        # Section: Model result
        y -= 26
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_left, y, "Model result")

        risk_label = str(log.get("prediction_result", "Unknown"))
        probability_str = self._probability_to_percent(log.get("probability"))
        input_summary = str(log.get("input_summary", ""))

        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(margin_left, y, f"Estimated risk: {risk_label}")
        y -= 14
        c.drawString(margin_left, y, f"Model probability: {probability_str}")
        y -= 14
        c.drawString(margin_left, y, f"Model type: Heart disease (Random Forest)")

        # Input summary
        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, y, "Input summary")
        y -= 14
        c.setFont("Helvetica", 10)
        text_obj = c.beginText()
        text_obj.setTextOrigin(margin_left, y)
        text_obj.setLeading(13)
        for line in input_summary.split(","):
            text_obj.textLine(line.strip())
        c.drawText(text_obj)

        # Explanation
        y = text_obj.getY() - 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, y, "Interpretation (educational only)")
        y -= 14
        explanation = self._heart_risk_explanation(risk_label)
        c.setFont("Helvetica", 10)
        text_obj = c.beginText()
        text_obj.setTextOrigin(margin_left, y)
        text_obj.setLeading(13)
        for line in self._wrap_text(explanation, max_chars=90):
            text_obj.textLine(line)
        c.drawText(text_obj)

        # Disclaimer at bottom
        disclaimer = self._medical_disclaimer()
        c.setFont("Helvetica", 9)
        text_obj = c.beginText()
        text_obj.setTextOrigin(margin_left, 25 * mm)
        text_obj.setLeading(11)
        for line in self._wrap_text(disclaimer, max_chars=95):
            text_obj.textLine(line)
        c.drawText(text_obj)

        return self._finish_canvas(c)

    # ------------------------------------------------------------------
    # Public API: Generate brain report
    # ------------------------------------------------------------------
    def generate_brain_report(self, user: User, log: Dict[str, Any]) -> BytesIO:
        """
        Create a PDF report for a brain-tumor prediction (4-class model).
        """
        c = self._create_canvas()
        width, height = A4

        margin_left = 20 * mm
        margin_top = height - 20 * mm

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin_left, margin_top, "Brain MRI AI Analysis Report")

        # Subtitle
        c.setFont("Helvetica", 10)
        c.drawString(
            margin_left,
            margin_top - 14,
            "Multi Disease Detection System – Educational AI output",
        )

        # Patient info
        y = margin_top - 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_left, y, "Patient information")

        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(margin_left, y, f"Name: {user.username}")
        y -= 14
        c.drawString(margin_left, y, f"Email: {user.email or 'N/A'}")
        y -= 14
        c.drawString(
            margin_left,
            y,
            f"Report generated from log ID: {log.get('id')} "
            f"on {self._format_datetime(log.get('created_at'))}",
        )

        # Model result
        y -= 26
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_left, y, "Model result")

        predicted_class = str(log.get("prediction_result", "Unknown"))
        probability_str = self._probability_to_percent(log.get("probability"))

        c.setFont("Helvetica", 10)
        y -= 14
        c.drawString(margin_left, y, f"Predicted class: {predicted_class}")
        y -= 14
        c.drawString(margin_left, y, f"Model probability: {probability_str}")
        y -= 14
        c.drawString(
            margin_left,
            y,
            "Model type: Brain tumor CNN (4-class: glioma, meningioma, pituitary, no_tumor)",
        )

        # Interpretation
        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_left, y, "Interpretation (educational only)")
        y -= 14
        explanation = self._brain_class_explanation(predicted_class)
        c.setFont("Helvetica", 10)
        text_obj = c.beginText()
        text_obj.setTextOrigin(margin_left, y)
        text_obj.setLeading(13)
        for line in self._wrap_text(explanation, max_chars=90):
            text_obj.textLine(line)
        c.drawText(text_obj)

        # Disclaimer at bottom
        disclaimer = self._medical_disclaimer()
        c.setFont("Helvetica", 9)
        text_obj = c.beginText()
        text_obj.setTextOrigin(margin_left, 25 * mm)
        text_obj.setLeading(11)
        for line in self._wrap_text(disclaimer, max_chars=95):
            text_obj.textLine(line)
        c.drawText(text_obj)

        return self._finish_canvas(c)

    # ------------------------------------------------------------------
    # Simple text wrapping helper
    # ------------------------------------------------------------------
    def _wrap_text(self, text: str, max_chars: int = 90) -> list[str]:
        """
        Naive word-wrap for long paragraphs for ReportLab.
        """
        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []

        for w in words:
            test_line = " ".join(current_line + [w])
            if len(test_line) <= max_chars:
                current_line.append(w)
            else:
                lines.append(" ".join(current_line))
                current_line = [w]

        if current_line:
            lines.append(" ".join(current_line))

        return lines


# Singleton instance
report_service = ReportService()
