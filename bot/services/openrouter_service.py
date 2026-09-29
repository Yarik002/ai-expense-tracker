import aiohttp
import json
import logging
from bot.config import settings
from bot.database.models import Category

class OpenRouterService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def categorize_expense(self, description: str, categories: list[Category]) -> Category | None:
        if not self.api_key:
            logging.warning("OPENROUTER_API_KEY is not set.")
            return None
            
        cat_dict = {cat.name.lower(): cat for cat in categories}
        cat_names = ", ".join([cat.name for cat in categories])
        
        prompt = f"""
        You are an expert financial categorization AI.
        User bought/spent on: "{description}"
        Available categories: {cat_names}
        
        Step 1: Analyze what "{description}" actually is (e.g., 'ноутбук' is electronics/Техника, 'медведь' is a toy/Игрушки, 'рис' is groceries/Продукты, 'семена' is Дача и Сад).
        Step 2: Compare your analysis against the available categories.
        IMPORTANT RULES:
        - Items for the house, garden, farming, or daily maintenance (seeds, plants, soil, tools, detergent, furniture) MUST go to 'Дача и Сад' or 'Быт', NOT 'Хобби'.
        - 'Хобби' (Hobby) is strictly for recreational activities, arts, crafts, and games.
        - If unsure between a specific category and a generic one, pick the specific one.
        Step 3: Verify your choice. Does another category fit better?
        Step 4: Output your final choice.
        
        You MUST respond ONLY with a valid JSON object in the following format, with no extra markdown formatting or text outside the JSON:
        {{
            "thought_process": "your step-by-step reasoning here",
            "category": "EXACT_CATEGORY_NAME"
        }}
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, headers=headers, json=data, timeout=15) as response:
                    if response.status == 200:
                        result = await response.json()
                        reply_text = result["choices"][0]["message"]["content"].strip()
                        
                        try:
                            # Clean up potential markdown formatting around JSON
                            if reply_text.startswith("```json"):
                                reply_text = reply_text[7:]
                            if reply_text.endswith("```"):
                                reply_text = reply_text[:-3]
                            reply_text = reply_text.strip()
                            
                            parsed_reply = json.loads(reply_text)
                            chosen_category = parsed_reply.get("category", "").strip().lower()
                            
                            # Match with dictionary
                            if chosen_category in cat_dict:
                                return cat_dict[chosen_category]
                                
                            # Fallback fuzzy match just in case
                            for cat_name, cat_obj in cat_dict.items():
                                if cat_name in chosen_category or chosen_category in cat_name:
                                    return cat_obj
                                    
                            logging.warning(f"OpenRouter chose '{chosen_category}' which does not match existing categories.")
                        except json.JSONDecodeError:
                            logging.error(f"OpenRouter returned invalid JSON: {reply_text}")
                    else:
                        error_text = await response.text()
                        logging.error(f"OpenRouter API error {response.status}: {error_text}")
        except Exception as e:
            logging.error(f"OpenRouter categorization failed: {e}")
            
        return None
