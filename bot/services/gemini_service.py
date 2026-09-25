import json
import asyncio
import google.generativeai as genai
from bot.config import settings

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.vision_model = genai.GenerativeModel(settings.GEMINI_VISION_MODEL)

    async def parse_receipt(self, image_bytes: bytes) -> dict:
        prompt = """
Analyze this receipt image. Extract ALL information:
1. Store/shop name
2. Each item with its price
3. Total amount
4. Date (if visible)
5. Currency

Respond ONLY in JSON format:
{
  "store": "Store Name",
  "items": [{"name": "Item 1", "price": 100.50}],
  "total": 500.00,
  "currency": "RUB",
  "date": "2024-01-15"
}
"""
        image_parts = [{"mime_type": "image/jpeg", "data": image_bytes}]
        
        def _generate():
            return self.vision_model.generate_content([prompt, image_parts[0]])
            
        try:
            response = await asyncio.to_thread(_generate)
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            return {"error": str(e)}

    async def categorize_expense(self, description: str, available_categories: list[str]) -> str:
        prompt = f"""
You are a financial categorization assistant. Given an expense description, pick the SINGLE best matching category.

Expense: {description}
Categories: {available_categories}

Respond with ONLY the category name, nothing else.
"""
        def _generate():
            return self.model.generate_content(prompt)
            
        try:
            response = await asyncio.to_thread(_generate)
            return response.text.strip()
        except Exception:
            return "Другое"

    async def parse_text_expense(self, text: str) -> dict:
        prompt = f"""
Parse this free-form expense text into a description, amount, and currency.
Text: "{text}"
Return ONLY JSON:
{{"description": "extracted description", "amount": 100.0, "currency": "RUB"}}
"""
        def _generate():
            return self.model.generate_content(prompt)
            
        try:
            response = await asyncio.to_thread(_generate)
            res_text = response.text.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:]
            elif res_text.startswith('```'):
                res_text = res_text[3:]
            if res_text.endswith('```'):
                res_text = res_text[:-3]
            return json.loads(res_text.strip())
        except Exception as e:
            return {"error": str(e)}

    async def parse_voice_text(self, text: str) -> dict:
        return await self.parse_text_expense(text)
