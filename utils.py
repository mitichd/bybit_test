"""
Допоміжні функції для трейдингового движка
"""

import logging
from constants import TradingConstants

def setup_logging():
    """
    Налаштування системи логування

    Returns:
        logging.Logger: Налаштований логер
    """
    # Створюємо логер
    logger = logging.getLogger(__name__)

    # Встановлюємо рівень логування
    logger.setLevel(logging.INFO)

    # Створюємо handler для консолі
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Створюємо handler для файлу
    file_handler = logging.FileHandler('logs/trading.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Створюємо formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Застосовуємо formatter до обох handler'ів
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Додаємо handler'и до логера
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def format_price(price):
    """
    Форматування ціни для виводу

    Args:
        price (float): Ціна для форматування

    Returns:
        str: Відформатована ціна
    """
    return f"${price:,.2f}"

def format_quantity(qty):
    """
    Форматування кількості для виводу

    Args:
        qty (float): Кількість для форматування

    Returns:
        str: Відформатована кількість
    """
    return f"{qty:.3f} BTC"

def calculate_quantity(amount, price):
    """
    Розрахунок кількості контрактів

    Args:
        amount (float): Сума в доларах
        price (float): Ціна активу

    Returns:
        float: Кількість контрактів
    """
    qty = amount / price
    qty = round(qty, TradingConstants.ROUND_DECIMALS)

    # Перевіряємо мінімальну кількість
    if qty < TradingConstants.MIN_QUANTITY:
        qty = TradingConstants.MIN_QUANTITY

    return qty

def calculate_tp_price(current_price, percent, side):
    """
    Розрахунок ціни TP ордера

    Args:
        current_price (float): Поточна ціна
        percent (float): Відсоток для TP
        side (str): Сторона позиції ('long' або 'short')

    Returns:
        float: Ціна TP ордера
    """
    if side == "short":
        return current_price * (1 - percent / 100)
    else:
        return current_price * (1 + percent / 100)

def calculate_dca_prices(current_price, range_percent, orders_count, side):
    """
    Розрахунок цін для DCA ордерів

    Args:
        current_price (float): Поточна ціна
        range_percent (float): Діапазон у відсотках
        orders_count (int): Кількість ордерів
        side (str): Сторона позиції

    Returns:
        list: Список цін для DCA ордерів
    """
    if side == "short":
        min_price = current_price * (1 - range_percent / 100)
        max_price = current_price
    else:
        min_price = current_price
        max_price = current_price * (1 + range_percent / 100)

    # Розраховуємо крок між ордерами
    price_step = (max_price - min_price) / (orders_count - 1)

    prices = []
    for i in range(orders_count):
        price = min_price + (i * price_step)
        prices.append(round(price, 2))

    return prices

def validate_config(config):
    """
    Валідація конфігурації

    Args:
        config (dict): Конфігурація для перевірки

    Raises:
        ValueError: При невалідній конфігурації
    """
    required_fields = [
        'symbol', 'side', 'market_order_amount',
        'leverage', 'tp_orders', 'limit_orders'
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Відсутнє обов'язкове поле: {field}")

    # Перевіряємо TP ордери
    if not isinstance(config['tp_orders'], list) or len(config['tp_orders']) == 0:
        raise ValueError("tp_orders повинен бути непустим списком")

    # Перевіряємо limit_orders
    limit_orders = config['limit_orders']
    if 'range_percent' not in limit_orders or 'orders_count' not in limit_orders:
        raise ValueError("limit_orders повинен містити range_percent та orders_count")

    return True

def get_api_symbol(symbol):
    """
    Конвертація символу для API

    Args:
        symbol (str): Символ торгівельної пари (наприклад: 'BTC/USDT')

    Returns:
        str: Символ для API (наприклад: 'BTCUSDT')
    """
    return symbol.replace('/', '')

def get_api_side(side):
    """
    Конвертація сторони для API

    Args:
        side (str): Сторона позиції ('long' або 'short')

    Returns:
        str: Сторона для API ('Buy' або 'Sell')
    """
    return "Sell" if side == "short" else "Buy"

def get_tp_side(side):
    """
    Конвертація сторони для TP ордерів

    Args:
        side (str): Сторона позиції ('long' або 'short')

    Returns:
        str: Сторона для TP ордерів
    """
    return "Buy" if side == "short" else "Sell"
