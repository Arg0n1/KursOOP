from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

FIXER_API_KEY = '99sNQZHfgvkhuA8CswPhNRQpg8PmI1ID'
TOKEN = '7766992589:AAGZVx_Jsd086BmLRMo8PwEmv0aCkaXMqos'
FIXER_BASE_URL = 'https://api.apilayer.com/fixer/'
HEADERS = {
    'apikey': FIXER_API_KEY
}

def get_available_currencies():
    response = requests.get(f"{FIXER_BASE_URL}symbols", headers=HEADERS)
    data = response.json()
    if data.get("success"):
        return data['symbols']
    else:
        return None

def get_currency_rate(base: str, symbol: str):
    response = requests.get(f"{FIXER_BASE_URL}latest", headers=HEADERS, params={
        'base': base,
        'symbols': symbol
    })
    data = response.json()
    if data.get("success"):
        return data['rates'].get(symbol)
    else:
        return None

def get_historical_data(base: str, symbol: str, days: int):
    rates = []
    dates = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        response = requests.get(f"{FIXER_BASE_URL}{date}", headers=HEADERS, params={
            'base': base,
            'symbols': symbol
        })
        data = response.json()
        if data.get("success"):
            rates.append(data['rates'].get(symbol))
            dates.append(date)
    return rates[::-1], dates[::-1]

def plot_currency_rates(dates, rates, base, symbol):
    plt.style.use('dark_background')
    plt.figure(figsize=(12, 6))
    formatted_dates = [datetime.strptime(date, '%Y-%m-%d').strftime('%m-%d') for date in dates]
    plt.plot(formatted_dates, rates, marker='o', linestyle='-', color='#1f77b4', label=f'{base} to {symbol}')
    plt.title(f"Exchange Rate: {base} to {symbol}", fontsize=16, color='white')
    plt.xlabel("Date", fontsize=12, color='white')
    plt.ylabel(f"Rate ({base} to {symbol})", fontsize=12, color='white')
    plt.grid(visible=True, linestyle='--', alpha=0.5, color='gray')
    plt.xticks(rotation=45, fontsize=10, color='white')
    plt.yticks(fontsize=10, color='white')
    plt.legend(fontsize=12, facecolor='black', edgecolor='white')

    plot_path = "exchange_rate_plot.png"
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    return plot_path

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        base, symbol = context.args
        rate = get_currency_rate(base.upper(), symbol.upper())
        if rate:
            await update.message.reply_text(f"Текущий курс конвертации {symbol.upper()} к {base.upper()}: {rate}")
        else:
            await update.message.reply_text("Ошибка получения данных.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, используйте заданный формат: /rate <FirstSymbol> <SecondSymbol>")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        base, symbol, days = context.args
        days = int(days)
        rates, dates = get_historical_data(base.upper(), symbol.upper(), days)

        if rates and dates:
            plot_path = plot_currency_rates(dates, rates, base.upper(), symbol.upper())
            caption = (f"График конвертации {base.upper()} в {symbol.upper()} "
                       f"за последние {days} дней.")
            await update.message.reply_photo(photo=open(plot_path, 'rb'), caption=caption)
            os.remove(plot_path)
        else:
            await update.message.reply_text("Ошибка получения данных.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, используйте заданный формат: /history <FirstSymbol> <SecondSymbol> <Days>")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = get_available_currencies()
    if symbols:
        message = "Доступные валюты:\n" + "\n".join([f"{code}: {name}" for code, name in symbols.items()])
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Ошибка получения данных.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте, у нас вы можете узнать актуальные курсы валют.\n"
        "Можете ознакомится с командами при помощи /help."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = (
        "/start - Начните общение\n"
        "/help - Список команд\n"
        "/rate <FirstSymbol> <SecondSymbol> - Получить текущий курс\n"
        "/history <FirstSymbol> <SecondSymbol> <Days> - Получить график за последние несколько дней\n"
        "/currency - Получить список доступных валют"
    )
    await update.message.reply_text(commands)

# Основная функция для запуска бота
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rate", rate_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("currency", currency_command))

    application.run_polling()

if __name__ == "__main__":
    print("Bot started...")
    main()
