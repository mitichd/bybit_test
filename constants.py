"""
Константи для трейдингового движка
"""

class TradingConstants:
    # Технічні обмеження Bybit API
    MIN_QUANTITY = 0.001
    ROUND_DECIMALS = 3

    # Налаштування моніторингу
    MONITORING_INTERVAL = 10  # секунди

    # Статуси движка
    STATUS_RUNNING = "running"
    STATUS_STOPPED = "stopped"
    STATUS_ERROR = "error"

    # Початковий розмір позиції для відстеження
    INITIAL_POSITION_SIZE = 0

    # Типи ордерів
    ORDER_TYPE_MARKET = "Market"
    ORDER_TYPE_LIMIT = "Limit"
    TIME_IN_FORCE_IOC = "IOC"
    TIME_IN_FORCE_GTC = "GTC"

    # Категорії торгівлі
    CATEGORY_LINEAR = "linear"
