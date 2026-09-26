import os
# Указываем, что мы работаем через Gradio, чтобы отключить конфликтующий веб-сервер
os.environ["RUNNING_IN_GRADIO"] = "true"

import gradio as gr
import threading
import asyncio
import sys

from bot.main import main as run_bot

def start_bot():
    """Запуск бота в отдельном потоке"""
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"Bot crashed: {e}")

# Запускаем бота параллельно с интерфейсом Gradio
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Создаем заглушку-интерфейс, чтобы Hugging Face считал приложение активным
def status():
    return "✅ AI Expense Tracker Bot успешно работает в фоновом режиме!"

demo = gr.Interface(
    fn=status, 
    inputs=[], 
    outputs="text", 
    title="Telegram Bot Status",
    description="Это техническая страница для поддержания работы Telegram бота на серверах Hugging Face."
)

if __name__ == "__main__":
    demo.launch()
