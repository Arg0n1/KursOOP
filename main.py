import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


FIXER_API_KEY = ''
TOKEN = ''
FIXER_BASE_URL = 'https://api.apilayer.com/fixer/'
HEADERS = {
    'apikey': FIXER_API_KEY
}


class CurrencyAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = FIXER_BASE_URL
        self.headers = {'apikey': self.api_key}

    def get_available_currencies(self):
        response = requests.get(f"{self.base_url}symbols", headers=self.headers)
        data = response.json()
        return data['symbols'] if data.get("success") else None

    def get_currency_rate(self, base, symbol):
        response = requests.get(f"{self.base_url}latest", headers=self.headers, params={
            'base': base,
            'symbols': symbol
        })
        data = response.json()
        return data['rates'].get(symbol) if data.get("success") else None

    def get_historical_data(self, base, symbol, days):
        rates, dates = [], []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            response = requests.get(f"{self.base_url}{date}", headers=self.headers, params={
                'base': base,
                'symbols': symbol
            })
            data = response.json()
            if data.get("success"):
                rates.append(data['rates'].get(symbol))
                dates.append(date)
        return rates[::-1], dates[::-1]

    def calculate_trend(self, rates):
        if len(rates) < 2:
            return "Нет данных для анализа"

        if rates[-1] > rates[0]:
            return "Растущий"

        elif rates[-1] < rates[0]:
            return "Падающий"

        return "Стабильный"

    def calculate_percentage_change(self, rates):
        if len(rates) < 2:
            return "Недостаточно данных для анализа"

        start_rate = rates[0]
        end_rate = rates[-1]
        percentage_change = ((end_rate - start_rate) / start_rate) * 100
        return f"{percentage_change:.2f}%"


class CurrencyPlotter:
    @staticmethod
    def plot_currency_rates(dates, rates, base, symbol):
        plt.style.use('dark_background')
        plt.figure(figsize=(12, 6))
        formatted_dates = [datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m') for date in dates]

        plt.plot(formatted_dates, rates, marker='o', linestyle='-', color='#1f77b4', label=f'{base} to {symbol}')
        plt.title(f"Курс конвертации: {base} к {symbol}", fontsize=16, color='white')
        plt.grid(visible=True, linestyle='--', alpha=0.5, color='gray')
        plt.xticks(rotation=45, fontsize=10, color='white')
        plt.yticks(fontsize=10, color='white')
        plt.legend(fontsize=12, facecolor='black', edgecolor='white')

        plot_path = "exchange_rate_plot.png"
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        return plot_path


class CurrencyBot:
    def __init__(self, api_key, token):
        self.currency_api = CurrencyAPI(api_key)
        self.application = Application.builder().token(token).build()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Здравствуйте, у нас вы можете узнать актуальные курсы валют.\n"
            "Можете ознакомится с командами при помощи /help."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        commands = (
            "/start - Начните общение\n"
            "/help - Список команд\n"
            "/rate <FirstSymbol> <SecondSymbol> - Получить текущий курс\n"
            "/history <FirstSymbol> <SecondSymbol> <Days> - Получить график за последние несколько дней\n"
            "/currency - Получить список доступных валют"
        )
        await update.message.reply_text(commands)

    async def rate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            base, symbol = context.args
            rate = self.currency_api.get_currency_rate(base.upper(), symbol.upper())
            if rate:
                keyboard = [[InlineKeyboardButton("🔄Обновить курс", callback_data=f"update_{base}_{symbol}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    text=f"Текущий курс конвертации {symbol.upper()} к {base.upper()}: {rate}",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("Ошибка получения данных.")
        except ValueError:
            await update.message.reply_text("Пожалуйста, используйте заданный формат: /rate <FirstSymbol> <SecondSymbol>")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def update_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data.split("_")
        if len(data) == 3 and data[0] == "update":
            base, symbol = data[1], data[2]
            rate = self.currency_api.get_currency_rate(base.upper(), symbol.upper())

            if rate:
                new_text = (
                    f"Текущий курс конвертации {symbol.upper()} к {base.upper()}: {rate}\n"
                    f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}"
                )

                keyboard = [[InlineKeyboardButton("🔄Обновить курс", callback_data=f"update_{base}_{symbol}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    text=new_text,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text="Ошибка получения данных."
                )

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            base, symbol, days = context.args
            days = int(days)
            rates, dates = self.currency_api.get_historical_data(base.upper(), symbol.upper(), days)

            if rates and dates:
                plot_path = CurrencyPlotter.plot_currency_rates(dates, rates, base.upper(), symbol.upper())
                trend = self.currency_api.calculate_trend(rates)
                percentage_change = self.currency_api.calculate_percentage_change(rates)
                caption = (f"График конвертации {base.upper()} в {symbol.upper()} "
                           f"за последние {days} дней.\n"
                           f"Тренд: {trend}.\n"
                           f"Процентное изменение за {days} дней: {percentage_change}.")
                await update.message.reply_photo(photo=open(plot_path, 'rb'), caption=caption)
                os.remove(plot_path)
            else:
                await update.message.reply_text("Ошибка получения данных.")
        except ValueError:
            await update.message.reply_text("Пожалуйста, используйте заданный формат: /history <FirstSymbol> <SecondSymbol> <Days>")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def currency_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        symbols = self.currency_api.get_available_currencies()
        if symbols:
            message = "Доступные валюты:\n" + "\n".join([f"{code}: {name}" for code, name in symbols.items()])
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Ошибка получения данных.")

    def run(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("rate", self.rate_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("currency", self.currency_command))
        self.application.add_handler(CallbackQueryHandler(self.update_button))
        self.application.run_polling()


if __name__ == "__main__":
    print("Bot started...")
    bot = CurrencyBot(FIXER_API_KEY, TOKEN)
    bot.run()