import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

# Завантажуємо змінні з .env
load_dotenv()

print(" Тестуємо підключення до Bybit Demo...")

# Підключаємося до Bybit Demo
session = HTTP(
    testnet=False,
    demo=True,
    api_key=os.getenv('BYBIT_API_KEY'),
    api_secret=os.getenv('BYBIT_API_SECRET')
)

try:
    # Тестуємо підключення
    print("📊 Отримуємо інформацію про акаунт...")
    account_info = session.get_account_info()
    print("✅ Підключення успішне!")
    print(f"Акаунт: {account_info}")

    # Отримуємо баланс
    print("💰 Отримуємо баланс...")
    balance = session.get_wallet_balance(accountType="UNIFIED")
    print(f"Баланс: {balance}")

    # Отримуємо інформацію про BTCUSDT
    print("📈 Отримуємо інформацію про BTCUSDT...")
    ticker = session.get_tickers(category="linear", symbol="BTCUSDT")
    print(f"BTCUSDT: {ticker}")

    print("\n Всі тести пройшли успішно!")
    print("✅ API ключі працюють правильно\n"
          "✅ Підключення до Demo успішне\n"
          "✅ Готові до торгівлі!")

except Exception as e:
    print(f"❌ Помилка підключення: {e}\n"
          f"Перевірте:\n"
          f"1. Чи створений ключ в Demo режимі\n"
          f"2. Чи правильно скопійовані ключі\n"
          f"3. Чи встановлені правильні дозволи")
