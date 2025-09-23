# 🚀 Bybit Trading Engine

Автоматичний трейдинговий движок для Bybit з підтримкою DCA та TP стратегій.

## 📋 Можливості

- ✅ Підключення до Bybit Demo/Testnet
- ✅ Автоматичне відкриття позицій
- ✅ DCA (Dollar Cost Averaging) ордери
- ✅ TP (Take Profit) ордери з автоматичним перерахунком
- ✅ Моніторинг позицій в реальному часі
- ✅ Graceful shutdown (безпечне закриття позицій)
- ✅ Модульна архітектура з docstrings
- ✅ Підготовка до веб-інтерфейсу

## 🏗️ Архітектура
bybit_test/
├── main.py # Головний файл запуску
├── trading_engine.py # Основний клас движка
├── constants.py # Глобальні константи
├── utils.py # Допоміжні функції
├── config.json # Конфігурація торгівлі
├── .env # API ключі (не комітити!)
├── requirements.txt # Python залежності
└── README.md # Документація

## ⚙️ Встановлення

1. **Клонуйте репозиторій:**
```bash
git clone <your-repo-url>
cd bybit_test
```

2. **Створіть віртуальне середовище:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

3. **Встановіть залежності:**
```bash
pip install -r requirements.txt
```

4. **Налаштуйте API ключі:**
```bash
cp .env.example .env
# Відредагуйте .env файл з вашими API ключами
```

## 🔧 Конфігурація

Створіть файл `config.json`:

```json
{
  "account": "Bybit/Testnet",
  "symbol": "BTC/USDT",
  "side": "short",
  "market_order_amount": 2000,
  "stop_loss_percent": 7,
  "trailing_sl_offset_percent": 3,
  "limit_orders_amount": 2000,
  "leverage": 10,
  "move_sl_to_breakeven": true,
  "tp_orders": [
    {"price_percent": 2.0, "quantity_percent": 25.0},
    {"price_percent": 5.0, "quantity_percent": 25.0},
    {"price_percent": 7.0, "quantity_percent": 25.0},
    {"price_percent": 3.0, "quantity_percent": 25.0}
  ],
  "limit_orders": {
    "range_percent": 5.0,
    "orders_count": 6,
    "engine_deal_duration_minutes": 110
  }
}
```

## 🚀 Запуск

```bash
python main.py
```

## 📊 Як це працює

1. **Запуск:** Движок підключається до Bybit Demo
2. **Відкриття позиції:** Створює market order з заданими параметрами
3. **TP ордери:** Розміщує серію limit ордерів для закриття при прибутку
4. **DCA ордери:** Створює ордери для усереднення позиції
5. **Моніторинг:** Відстежує позиції та перераховує TP при змінах
6. **Зупинка:** Безпечно закриває позиції та скасовує ордери

## 🔧 Налаштування API

1. Зайдіть на [Bybit Demo Trading](https://testnet.bybit.com/)
2. Створіть API ключі
3. Додайте їх в `.env` файл:

```env
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
```

## 📈 Стратегія торгівлі

### **DCA (Dollar Cost Averaging)**
- Розміщує ордери в діапазоні цін
- Усереднює ціну входу при падінні
- Автоматично перераховує TP при виконанні

### **TP (Take Profit)**
- Множинні цілі прибутку
- Автоматичне оновлення при зміні середньої ціни
- Часткове закриття позиції

## ⚠️ Важливо

- **Використовуйте тільки Demo/Testnet** для тестування
- **Ніколи не додавайте `.env` в Git**
- **Перевіряйте конфігурацію** перед запуском
- **Моніторьте позиції** під час роботи
- **Використовуйте Ctrl+C** для безпечної зупинки

## 🛠️ Розробка

### **Структура коду**
- `TradingEngine` - основний клас движка
- `utils.py` - допоміжні функції
- `constants.py` - глобальні константи
- Модульна архітектура для легкого розширення

### **Додавання нових функцій**
1. Додайте функцію в `utils.py`
2. Імпортуйте в `trading_engine.py`
3. Використовуйте в методах класу
4. Додайте docstring

## 🔮 Майбутні плани

- [ ] Веб-інтерфейс для управління
- [ ] REST API для зовнішнього керування
- [ ] Додаткові стратегії торгівлі
- [ ] Більше бірж (Binance, OKX)
- [ ] Telegram бот для сповіщень

## �� Підтримка

При виникненні проблем:
1. Перевірте API ключі
2. Перевірте конфігурацію
3. Перегляньте логи
4. Створіть issue в репозиторії

## 👨‍�� Автор
- **MTCH**

_Розроблено як тестове завдання для позиції Python розробника_
