"""
Константи для трейдингового движка
"""

class TradingConstants:
    # Технічні обмеження Bybit API
    MIN_QUANTITY = 0.001
    ROUND_DECIMALS = 3

    # Налаштування моніторингу
    MONITORING_INTERVAL = 10  # секунди

    # Налаштування API
    API_TIMEOUT = 30  # секунди

    # Статуси движка
    STATUS_RUNNING = "running"
    STATUS_STOPPED = "stopped"
    STATUS_ERROR = "error"
