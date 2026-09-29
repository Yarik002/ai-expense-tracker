from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.database.engine import async_session
from bot.database.models import User
from bot.services.analytics_service import AnalyticsService
from bot.keyboards.inline import analytics_keyboard, back_keyboard
from bot.utils.formatters import format_amount, format_monthly_report, format_comparison_report

router = Router()


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def quick_stats(message: Message, db_user: User):
    """Быстрая статистика за текущий месяц."""
    now = datetime.now()
    async with async_session() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_monthly_summary(db_user.id, now.year, now.month)
    
    theme = db_user.design_theme or "standard"
    text = format_monthly_report(summary, db_user.currency, theme=theme)
    text += "\n\n📊 /menu → Аналитика для подробного анализа"
    await message.answer(text)


@router.callback_query(F.data == "analytics")
async def show_analytics_menu(callback: CallbackQuery, db_user: User):
    is_premium = db_user.subscription_type == 'premium'
    await callback.message.edit_text(
        "📊 <b>Аналитика</b>\n\nВыберите период:",
        reply_markup=analytics_keyboard(is_premium=is_premium),
    )
    await callback.answer()


@router.callback_query(F.data == "analytics_week")
async def show_analytics_week(callback: CallbackQuery, db_user: User):
    async with async_session() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_weekly_summary(db_user.id)
    
    if summary["expense_count"] == 0:
        text = "📭 На этой неделе пока нет расходов."
    else:
        text = "<b>📅 Статистика за неделю</b>\n\n"
        text += f"💰 <b>Итого:</b> {format_amount(summary['total'], db_user.currency)}\n"
        text += f"📦 Расходов: {summary['expense_count']}\n"
        text += f"📊 Среднее в день: {format_amount(summary['avg_per_day'], db_user.currency)}\n\n"
        
        if summary["by_category"]:
            text += "<b>По категориям:</b>\n"
            for cat in summary["by_category"]:
                text += f"  {cat['emoji']} {cat['name']}: {format_amount(cat['total'], db_user.currency)} ({cat['percentage']}%)\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard("analytics"))
    await callback.answer()


@router.callback_query(F.data == "analytics_month")
async def show_analytics_month(callback: CallbackQuery, db_user: User):
    now = datetime.now()
    async with async_session() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_monthly_summary(db_user.id, now.year, now.month)
    
    theme = db_user.design_theme or "standard"
    text = format_monthly_report(summary, db_user.currency, theme=theme)
    await callback.message.edit_text(text, reply_markup=back_keyboard("analytics"))
    await callback.answer()


@router.callback_query(F.data == "analytics_compare")
async def show_analytics_compare(callback: CallbackQuery, db_user: User):
    async with async_session() as session:
        analytics = AnalyticsService(session)
        comparison = await analytics.compare_with_previous_month(db_user.id)
    
    text = format_comparison_report(comparison, db_user.currency)
    await callback.message.edit_text(text, reply_markup=back_keyboard("analytics"))
    await callback.answer()


@router.callback_query(F.data == "analytics_top")
async def show_analytics_top(callback: CallbackQuery, db_user: User):
    now = datetime.now()
    async with async_session() as session:
        analytics = AnalyticsService(session)
        top = await analytics.get_top_expenses(db_user.id, now.year, now.month, limit=5)
    
    if not top:
        text = "📭 В этом месяце пока нет расходов."
    else:
        text = "<b>🔝 Топ-5 расходов за месяц:</b>\n\n"
        for i, exp in enumerate(top, 1):
            emoji = exp.category.emoji if exp.category else "❓"
            text += f"{i}. {emoji} {exp.description} — <b>{format_amount(exp.amount, exp.currency)}</b>\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard("analytics"))
    await callback.answer()

import io
from aiogram.types import BufferedInputFile, URLInputFile
import urllib.parse
from bot.database.repositories import ExpenseRepository
from bot.services.analytics_service import AnalyticsService

@router.callback_query(F.data == "export_csv")
async def export_excel(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer("Только для Premium!", show_alert=True)
        return
        
    now = datetime.now()
    async with async_session() as session:
        repo = ExpenseRepository(session)
        expenses = await repo.get_user_expenses(db_user.id, limit=1000)
        
    if not expenses:
        await callback.answer("Нет данных для выгрузки.", show_alert=True)
        return
        
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Мои Расходы"
    
    # Headers
    headers = ["ID", "Дата", "Время", "Категория", "Описание", "Сумма", "Валюта"]
    ws.append(headers)
    
    # Styling headers
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    border = Border(
        left=Side(border_style="thin", color="000000"),
        right=Side(border_style="thin", color="000000"),
        top=Side(border_style="thin", color="000000"),
        bottom=Side(border_style="thin", color="000000")
    )
    
    for col_num, cell in enumerate(ws[1], 1):
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        
    # Data rows
    for exp in expenses:
        date_obj = exp.created_at if exp.created_at else datetime.now()
        cat_name = exp.category.name if exp.category else "Без категории"
        
        row = [
            exp.id,
            date_obj.strftime("%d.%m.%Y"),
            date_obj.strftime("%H:%M"),
            cat_name,
            exp.description,
            float(exp.amount),
            exp.currency
        ]
        ws.append(row)
        
        # Style row borders
        for cell in ws[ws.max_row]:
            cell.border = border
            if cell.column == 6: # Sum column
                cell.number_format = '#,##0.00'
                
    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col_letter].width = adjusted_width

    # Filter
    ws.auto_filter.ref = ws.dimensions
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    file = BufferedInputFile(output.getvalue(), filename=f"expenses_{now.strftime('%Y_%m')}.xlsx")
    
    await callback.message.answer_document(
        document=file, 
        caption="📊 <b>Ваш профессиональный финансовый отчет готов!</b>\nОтлично открывается в Excel и содержит автофильтры."
    )
    await callback.answer()

@router.callback_query(F.data == "smart_chart")
async def smart_chart(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer("Только для Premium!", show_alert=True)
        return
        
    now = datetime.now()
    async with async_session() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_monthly_summary(db_user.id, now.year, now.month)
        
    if summary["expense_count"] == 0:
        await callback.answer("Нет расходов для графика.", show_alert=True)
        return
        
    # Beautiful Professional Chart Colors
    labels = []
    data = []
    for cat in summary["by_category"]:
        labels.append(f"{cat['emoji']} {cat['name']}")
        data.append(float(cat['total']))
        
    color_palette = [
        "rgb(54, 162, 235)", "rgb(255, 99, 132)", "rgb(255, 159, 64)",
        "rgb(75, 192, 192)", "rgb(153, 102, 255)", "rgb(255, 205, 86)",
        "rgb(201, 203, 207)", "rgb(100, 255, 100)", "rgb(150, 150, 150)"
    ]
    
    # Format a sleek doughnut chart
    import json
    chart_config = {
        "type": "doughnut",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": data,
                "backgroundColor": color_palette[:len(data)],
                "borderWidth": 2,
                "borderColor": "#ffffff"
            }]
        },
        "options": {
            "plugins": {
                "legend": {
                    "position": "right",
                    "labels": {
                        "fontSize": 14,
                        "fontStyle": "bold",
                        "fontColor": "#333",
                        "padding": 20
                    }
                },
                "datalabels": {
                    "color": "#fff",
                    "font": {
                        "weight": "bold",
                        "size": 14
                    },
                    "formatter": "function(value, context) { return Math.round(value) + ' " + db_user.currency + "'; }"
                }
            },
            "cutoutPercentage": 60,
            "layout": {
                "padding": 20
            }
        }
    }
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    chart_url = f"https://quickchart.io/chart?c={encoded_config}&w=800&h=450&bkg=white"
    
    caption = "📈 <b>Ваш финансовый отчет</b>\n\n"
    if len(summary["by_category"]) > 0:
        top_cat = summary["by_category"][0]
        caption += f"💎 <b>Аналитика ИИ:</b> Наибольшая доля ваших расходов ({top_cat['percentage']}%) приходится на категорию «{top_cat['name']}».\n"
        caption += f"Суммарно вы потратили на неё {format_amount(top_cat['total'], db_user.currency)}."
        
    photo = URLInputFile(chart_url)
    await callback.message.answer_photo(photo=photo, caption=caption)
    await callback.answer()

from bot.services.gemini_service import GeminiService

from bot.services.gemini_service import GeminiService
import asyncio

@router.callback_query(F.data == 'ai_advice')
async def ai_advice(callback: CallbackQuery, db_user: User):
    if db_user.subscription_type != 'premium':
        await callback.answer('⭐ Только для Premium!', show_alert=True)
        return
        
    await callback.message.edit_text('🤖 Анализирую ваши финансы... Пожалуйста, подождите.')
    
    now = datetime.now()
    async with async_session() as session:
        from bot.services.analytics_service import AnalyticsService
        analytics = AnalyticsService(session)
        summary = await analytics.get_monthly_summary(db_user.id, now.year, now.month)
        
    expenses_text = ', '.join([f"{c['name']}: {c['total']}" for c in summary['by_category']])
    
    prompt = f"""
Вы профессиональный и вежливый финансовый ИИ-советник. 
У пользователя текущий баланс: {db_user.balance} {db_user.currency}.
Траты за этот месяц по категориям: {expenses_text}.
Напиши короткий (до 3-4 абзацев) полезный совет по личным финансам, учитывая эти данные. 
Пиши дружелюбно, используй эмодзи и предложи, как лучше оптимизировать расходы или на чем сэкономить.
"""
    
    gemini = GeminiService()
    try:
        def _generate():
            return gemini.model.generate_content(prompt)
        response = await asyncio.to_thread(_generate)
        advice = response.text
    except Exception as e:
        advice = "❌ К сожалению, не удалось получить совет от ИИ в данный момент. Попробуйте позже."
        
    text = f"🤖 <b>Совет от Финансового ИИ</b>\n\n💵 Баланс: <b>{format_amount(db_user.balance, db_user.currency)}</b>\n\n{advice}"
    await callback.message.edit_text(text, reply_markup=back_keyboard('analytics'))
    await callback.answer()
