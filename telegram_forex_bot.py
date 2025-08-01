import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from datetime import datetime

# Для Binance API
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

# --- ВАШІ КОНФІГУРАЦІЇ ---
# Ваш токен Telegram Бота, отриманий від @BotFather
BOT_TOKEN = '7864681243:AAGcoKhWmbV3hIov43phiOnWKJ0RW3obhWw' 

# Ваш API ключ Alpha Vantage, отриманий з https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY = "4966249ON65O2U9F" 
# --- КІНЕЦЬ КОНФІГУРАЦІЙ ---

# Ініціалізація клієнта Binance (для публічних даних ключі не потрібні)
# Якщо колись знадобляться приватні ключі для торгівлі, їх треба буде вказати тут:
# binance_client = BinanceClient("ВАШ_BINANCE_API_KEY", "ВАШ_BINANCE_API_СЕКРЕТ")
binance_client = BinanceClient("", "") # Пусті рядки, оскільки ключі не потрібні для публічних даних

# URL для отримання щоденних даних Forex з Alpha Vantage
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Список доступних валютних пар для кнопок
# 'callback_data' - це дані, які бот отримає, коли користувач натисне кнопку.
# Ми використовуємо префікси, щоб розрізняти Форекс і Крипто пари.
AVAILABLE_PAIRS = {
    # Основні Форекс пари (додані з розбитими символами для Alpha Vantage)
    "EUR/USD (Форекс)": "forex_EURUSD",
    "GBP/USD (Форекс)": "forex_GBPUSD",
    "USD/JPY (Форекс)": "forex_USDJPY",
    "USD/CHF (Форекс)": "forex_USDCHF",
    "AUD/USD (Форекс)": "forex_AUDUSD",
    "USD/CAD (Форекс)": "forex_USDCAD",
    ""
    "NZD/USD (Форекс)": "forex_NZDUSD",
    "EUR/GBP (Форекс)": "forex_EURGBP",
    "EUR/JPY (Форекс)": "forex_EURJPY",
    "EUR/CAD (Форекс)": "forex_EURCAD", 
    "USD/RUB (Форекс)": "forex_USDRUB", # Додано, якщо цікаво, але Alpha Vantage може мати обмеження
    "EUR/RUB (Форекс)": "forex_EURRUB", # Додано, якщо цікаво, але Alpha Vantage може мати обмеження

    # Основні Крипто пари (на Binance їхні символи завжди разом, наприклад BTCUSDT)
    "BTC/USDT (Крипто)": "crypto_BTCUSDT",
    "ETH/USDT (Крипто)": "crypto_ETHUSDT",
    "BNB/USDT (Крипто)": "crypto_BNBUSDT",
    "XRP/USDT (Крипто)": "crypto_XRPUSDT",
    "SOL/USDT (Крипто)": "crypto_SOLUSDT",
    "ADA/USDT (Крипто)": "crypto_ADAUSDT",
    "DOGE/USDT (Крипто)": "crypto_DOGEUSDT",
    "DOT/USDT (Крипто)": "crypto_DOTUSDT",
    "LTC/USDT (Крипто)": "crypto_LTCUSDT",
    "BCH/USDT (Крипто)": "crypto_BCHUSDT",
    "LINK/USDT (Крипто)": "crypto_LINKUSDT",
    "UNI/USDT (Крипто)": "crypto_UNIUSDT",
    "AVAX/USDT (Крипто)": "crypto_AVAXUSDT",
    "MATIC/USDT (Крипто)": "crypto_MATICUSDT",
    "TRX/USDT (Крипто)": "crypto_TRXUSDT",
    "SHIB/USDT (Крипто)": "crypto_SHIBUSDT",
    "DOGE/BUSD (Крипто)": "crypto_DOGEBUSD", # Приклад іншої базової валюти, якщо є на Binance
    "BTC/BUSD (Крипто)": "crypto_BTCBUSD",
    "ETH/BUSD (Крипто)": "crypto_ETHBUSD",
    "XRP/BUSD (Крипто)": "crypto_XRPBUSD",
}


def get_forex_data(from_currency, to_currency, api_key):
    """
    Отримує щоденні дані по валютній парі з Alpha Vantage.
    """
    params = {
        "function": "FX_DAILY",
        "from_symbol": from_currency,
        "to_symbol": to_currency,
        "apikey": api_key
    }
    
    try:
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params)
        response.raise_for_status() 
        data = response.json()
        
        if "Time Series FX (Daily)" in data:
            return data["Time Series FX (Daily)"]
        elif "Error Message" in data:
            print(f"Помилка Alpha Vantage: {data['Error Message']}")
            return None
        elif "Note" in data and "Thank you for using Alpha Vantage!" in data["Note"]:
            print("Alpha Vantage Note: Ви перевищили ліміт запитів на хвилину/день.")
            print("Зачекайте трохи і спробуйте ще раз або розгляньте преміум-план.")
            return None
        else:
            print("Неочікуваний формат відповіді від Alpha Vantage:", data)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Помилка запиту до Alpha Vantage: {e}")
        return None
    except ValueError as e:
        print(f"Помилка розбору JSON відповіді: {e}")
        return None
    except Exception as e:
        print(f"Невідома помилка при отриманні даних Alpha Vantage: {e}")
        return None

def analyze_forex_signal(forex_data):
    """
    Аналізує дані Forex і генерує простий сигнал.
    """
    if not forex_data or len(forex_data) < 2:
        return "Недостатньо даних для аналізу."
    
    dates = sorted(forex_data.keys(), reverse=True) 
    
    latest_date = dates[0]
    previous_date = dates[1]
    
    try:
        latest_close = float(forex_data[latest_date]['4. close'])
        previous_close = float(forex_data[previous_date]['4. close'])
        
        if latest_close > previous_close:
            return "ВГОРУ (ціна зростає)"
        else:
            return "ВНИЗ (ціна падає або стабільна)"
    except KeyError:
        return "Помилка при отриманні цін закриття. Перевірте формат даних."
    except ValueError:
        return "Помилка конвертації ціни в число. Перевірте формат даних."
    except Exception as e:
        return f"Помилка аналізу сигналу: {e}"

# --- НОВІ ФУНКЦІЇ ДЛЯ BINANCE ---

def get_binance_klines(symbol, interval='1d', limit=2):
    """
    Отримує дані про свічки (Klines) з Binance API.
    Ми беремо 2 свічки (останню та попередню).
    """
    try:
        klines = binance_client.get_historical_klines(symbol, interval, limit=limit)
        return klines
    except BinanceAPIException as e:
        print(f"Помилка Binance API для {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Невідома помилка при отриманні даних Binance для {symbol}: {e}")
        return None

def analyze_crypto_signal(klines):
    """
    Аналізує дані про свічки Binance і генерує простий сигнал.
    """
    if not klines or len(klines) < 2:
        return "Недостатньо даних для аналізу."
    
    latest_kline = klines[-1]
    previous_kline = klines[-2]
    
    try:
        latest_close = float(latest_kline[4]) # Індекс 4 - це ціна закриття
        previous_close = float(previous_kline[4])
        
        if latest_close > previous_close:
            return "ВГОРУ (ціна зростає)"
        else:
            return "ВНИЗ (ціна падає або стабільна)"
    except IndexError:
        return "Некоректний формат даних свічок."
    except ValueError:
        return "Помилка конвертації ціни в число. Перевірте формат даних."
    except Exception as e:
        return f"Помилка аналізу крипто сигналу: {e}"

# --- Функції для Telegram Бота ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /start та показує кнопки вибору пар."""
    keyboard_buttons = []
    # Створюємо кнопки з доступних пар
    # Розбиваємо на кілька рядків, щоб кнопки не були занадто широкими
    row = []
    for text, callback_data in AVAILABLE_PAIRS.items():
        row.append(InlineKeyboardButton(text, callback_data=callback_data))
        if len(row) >= 2: # 2 кнопки в рядку
            keyboard_buttons.append(row)
            row = []
    if row: # Додати залишок, якщо є
        keyboard_buttons.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    await update.message.reply_text(
        'Привіт! Я твій торговий помічник. Оберіть валютну пару для аналізу:',
        reply_markup=reply_markup
    )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання на кнопки під повідомленням."""
    query = update.callback_query
    await query.answer() # Відповідаємо на callback, щоб прибрати "годинник" з кнопки

    callback_data = query.data
    
    # Розбиваємо дані зворотного виклику, щоб визначити тип пари та її символ
    parts = callback_data.split('_')
    pair_type = parts[0] # 'forex' або 'crypto'
    symbol = parts[1]    # 'EURCAD', 'BTCUSDT' тощо

    await query.edit_message_text(f"Аналізую ринок **{symbol}**, зачекайте...") # Оновлюємо повідомлення

    if pair_type == "forex":
        # Alpha Vantage очікує розділення на from_currency та to_currency
        if len(symbol) != 6: # Перевірка формату наприклад "EURUSD" має бути 6 символів
            message = f"Помилка: Неправильний формат символу Форекс-пари '{symbol}'. Очікується 6 символів (наприклад, EURUSD)."
            await query.edit_message_text(message)
            return

        from_currency = symbol[:3] 
        to_currency = symbol[3:] 
        
        forex_data = get_forex_data(from_currency, to_currency, ALPHA_VANTAGE_API_KEY)

        if forex_data:
            signal = analyze_forex_signal(forex_data)
            latest_date = sorted(forex_data.keys(), reverse=True)[0]
            latest_close_price = forex_data[latest_date]['4. close']

            message = (
                f"Останні дані **{symbol}** (дата: {latest_date}):\n"
                f"Ціна закриття: {latest_close_price}\n"
                f"Мій простий аналіз каже: **{signal}**\n\n"
                "Пам'ятайте: це дуже спрощений аналіз і не є фінансовою порадою!"
            )
            await query.edit_message_text(message, reply_markup=query.message.reply_markup) # Зберігаємо кнопки
        else:
            await query.edit_message_text(
                f"Не вдалося отримати дані для **{symbol}**. Можливо, проблема з API ключем, лімітом запитів Alpha Vantage або інтернет-з'єднанням.",
                reply_markup=query.message.reply_markup # Зберігаємо кнопки
            )
    elif pair_type == "crypto":
        klines = get_binance_klines(symbol)

        if klines:
            signal = analyze_crypto_signal(klines)
            latest_close_price = float(klines[-1][4]) # Індекс 4 - це ціна закриття

            message = (
                f"Останні дані **{symbol}** (закриття): {latest_close_price}\n"
                f"Мій простий аналіз каже: **{signal}**\n\n"
                "Пам'ятайте: це дуже спрощений аналіз і не є фінансовою порадою!"
            )
            await query.edit_message_text(message, reply_markup=query.message.reply_markup) # Зберігаємо кнопки
        else:
            await query.edit_message_text(
                f"Не вдалося отримати дані для **{symbol}**. Перевірте правильність символу або спробуйте пізніше.",
                reply_markup=query.message.reply_markup # Зберігаємо кнопки
            )
    else:
        await query.edit_message_text("Невідома пара. Будь ласка, оберіть зі списку.", reply_markup=query.message.reply_markup) # Зберігаємо кнопки


# --- Основна функція для запуску бота ---
def main() -> None:
    """Запускає бота."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button_click)) 

    print("Бот запущено! Надсилайте команду /start у Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()