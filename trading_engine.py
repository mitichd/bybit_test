"""
Трейдинговий движок з DCA та TP стратегіями
"""

import os
import json
import time
import signal
import sys
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from constants import TradingConstants
from utils import (
    setup_logging, format_price, format_quantity,
    calculate_quantity, calculate_tp_price, calculate_dca_prices,
    validate_config, get_api_symbol, get_api_side, get_tp_side
)

class TradingEngine:
    """
    Основний клас трейдингового движка

    Відповідає за підключення до Bybit API, управління позиціями,
    розміщення ордерів та моніторинг торгівлі.
    """

    def __init__(self):
        """
        Ініціалізація трейдингового движка

        Створює з'єднання з Bybit API, налаштовує логування
        та підготовлює движок до роботи.
        """
        # Налаштування логування
        self._setup_logging()

        # Завантаження змінних середовища
        load_dotenv()

        # Підключення до Bybit
        self._connect_to_exchange()

        # Стан движка
        self.is_running = False
        self.config = None
        self.start_time = None

        # Обробка сигналів для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_logging(self):
        """
        Налаштування системи логування

        Встановлює формат логів та рівень деталізації.
        """
        self.logger = setup_logging()

    def _connect_to_exchange(self):
        """
        Підключення до Bybit API

        Встановлює з'єднання з Bybit Demo/Testnet API
        використовуючи ключі з .env файлу.

        Raises:
            Exception: При помилці підключення
        """
        try:
            self.session = HTTP(
                testnet=False,
                demo=True,
                api_key=os.getenv('BYBIT_API_KEY'),
                api_secret=os.getenv('BYBIT_API_SECRET')
            )
            self.logger.info("�� Трейдинговий движок запущено!")
            self.logger.info("📊 Підключення до Bybit Demo успішне!")
        except Exception as e:
            self.logger.error(f"❌ Помилка підключення: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """
        Обробка сигналів для graceful shutdown

        Args:
            signum: Номер сигналу
            frame: Поточний кадр стеку
        """
        self.logger.info(f"🛑 Отримано сигнал {signum}. Закриваємо позиції...")
        self.stop()
        sys.exit(0)

    def load_config(self):
        """
        Завантаження конфігурації з JSON файлу

        Читає config.json, валідує його та зберігає в self.config

        Returns:
            dict or None: Конфігурація або None при помилці
        """
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)

            # Валідуємо конфігурацію
            validate_config(self.config)

            self.logger.info(f"✅ Конфігурація завантажена: {self.config['symbol']}")
            return self.config
        except FileNotFoundError:
            self.logger.error("❌ Файл config.json не знайдено")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Помилка парсингу JSON: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"❌ Помилка валідації конфігурації: {e}")
            return None

    def start(self):
        """
        Запуск торгівлі

        Завантажує конфігурацію, відкриває позицію,
        розміщує TP та DCA ордери, починає моніторинг.

        Returns:
            None
        """
        if self.is_running:
            self.logger.warning("⚠️ Движок вже працює")
            return

        # Завантажуємо конфігурацію
        if not self.load_config():
            return

        self.is_running = True
        self.start_time = time.time()

        # Запускаємо основний цикл
        self._run_trading_loop()

    def stop(self):
        """
        Зупинка торгівлі з закриттям позицій

        Закриває всі відкриті позиції та скасовує ордери
        перед зупинкою движка.
        """
        if not self.is_running:
            self.logger.warning("⚠️ Движок не працює")
            return

        self.logger.info("🛑 Зупиняємо торгівлю...")

        # Закриваємо всі позиції
        self.close_all_positions()

        self.is_running = False
        self.logger.info("⏹️ Торгівля зупинена")

    def _run_trading_loop(self):
        """
        Основний цикл торгівлі

        Виконує послідовність: отримання ціни → відкриття позиції →
        розміщення TP/DCA ордерів → моніторинг.
        """
        self.logger.info("\n�� ЗАПУСК ТРЕЙДИНГОВОГО ДВИЖКА")
        self.logger.info("=" * 50)

        # Отримуємо поточну ціну
        current_price = self.get_current_price(self.config['symbol'])
        if not current_price:
            return

        # Відкриваємо позицію
        order = self.open_position(self.config)
        if not order:
            return

        # Ставимо TP ордери
        self.place_tp_orders(self.config, current_price)

        # Ставимо DCA ордери
        self.place_dca_orders(self.config, current_price)

        # Моніторинг
        self.logger.info("\n�� Починаємо моніторинг...")
        api_symbol = self.config['symbol'].replace('/', '')

        while self.is_running:
            self.monitor_positions(api_symbol)
            time.sleep(TradingConstants.MONITORING_INTERVAL)

    def get_current_price(self, symbol):
        """
        Отримання поточної ціни активу

        Args:
            symbol (str): Символ торгівельної пари (наприклад: 'BTC/USDT')

        Returns:
            float or None: Поточна ціна або None при помилці
        """
        try:
            api_symbol = get_api_symbol(symbol)
            response = self.session.get_tickers(category="linear", symbol=api_symbol)

            if response['retCode'] == 0 and response['result']['list']:
                price = float(response['result']['list'][0]['lastPrice'])
                self.logger.info(f"💰 Поточна ціна {symbol}: {format_price(price)}")
                return price
            else:
                self.logger.error(f"❌ Помилка отримання ціни: {response}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Помилка отримання ціни: {e}")
            return None

    def open_position(self, config):
        """
        Відкриття позиції

        Встановлює leverage, розраховує кількість контрактів
        та відкриває market order.

        Args:
            config (dict): Конфігурація торгівлі

        Returns:
            dict or None: Результат ордера або None при помилці
        """
        symbol = config['symbol']
        side = config['side']
        amount = config['market_order_amount']
        leverage = config['leverage']

        api_side = get_api_side(side)
        api_symbol = get_api_symbol(symbol)

        self.logger.info(f"�� Відкриваємо позицію: {side} ${amount} {symbol} (x{leverage})")

        try:
            # Спробуємо встановити leverage
            try:
                self.session.set_leverage(
                    category="linear",
                    symbol=api_symbol,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage)
                )
                self.logger.info(f"✅ Leverage встановлено: {leverage}x")
            except Exception as leverage_error:
                # Ігноруємо помилку leverage - він вже встановлений
                if "110043" in str(leverage_error):
                    self.logger.info(f"ℹ️ Leverage вже встановлений: {leverage}x")
                else:
                    self.logger.warning(f"⚠️ Помилка leverage: {leverage_error}")

            # Отримуємо поточну ціну для розрахунку кількості
            current_price = self.get_current_price(symbol)
            if not current_price:
                return None

            # Розраховуємо кількість контрактів
            qty = calculate_quantity(amount, current_price)

            self.logger.info(f"�� Сума: ${amount}, Ціна: {format_price(current_price)}, Кількість: {format_quantity(qty)}")

            # Відкриваємо позицію
            order = self.session.place_order(
                category="linear",
                symbol=api_symbol,
                side=api_side,
                orderType="Market",
                qty=str(qty),
                timeInForce="IOC"
            )

            self.logger.info(f"✅ Позиція відкрита: {order}")
            return order

        except Exception as e:
            self.logger.error(f"❌ Помилка відкриття позиції: {e}")
            return None

    def place_tp_orders(self, config, current_price):
        """
        Розміщення TP (Take Profit) ордерів

        Створює серію limit ордерів для закриття позиції
        при досягненні цільових цін.

        Args:
            config (dict): Конфігурація торгівлі
            current_price (float): Поточна ціна активу
        """
        symbol = config['symbol']
        side = config['side']
        tp_orders = config['tp_orders']

        api_symbol = get_api_symbol(symbol)
        api_side = get_tp_side(side)

        self.logger.info(f"�� Розміщуємо {len(tp_orders)} TP ордерів...")

        for i, tp_order in enumerate(tp_orders):
            try:
                # Розраховуємо ціну TP
                tp_price = calculate_tp_price(current_price, tp_order['price_percent'], side)

                # Розраховуємо кількість
                qty = calculate_quantity(
                    (tp_order['quantity_percent'] / 100) * config['market_order_amount'],
                    current_price
                )

                # Розміщуємо ордер
                order = self.session.place_order(
                    category="linear",
                    symbol=api_symbol,
                    side=api_side,
                    orderType="Limit",
                    qty=str(qty),
                    price=str(round(tp_price, 2)),
                    timeInForce="GTC"
                )

                self.logger.info(f"✅ TP ордер {i+1}: {tp_order['price_percent']}% -> {format_price(tp_price)} ({format_quantity(qty)})")

            except Exception as e:
                self.logger.error(f"❌ Помилка TP ордера {i+1}: {e}")

    def place_dca_orders(self, config, current_price):
        """
        Розміщення DCA (Dollar Cost Averaging) ордерів

        Створює серію limit ордерів для усереднення позиції
        в заданому діапазоні цін.

        Args:
            config (dict): Конфігурація торгівлі
            current_price (float): Поточна ціна активу
        """
        symbol = config['symbol']
        side = config['side']
        limit_orders = config['limit_orders']

        api_symbol = get_api_symbol(symbol)
        api_side = get_api_side(side)

        range_percent = limit_orders['range_percent']
        orders_count = limit_orders['orders_count']

        self.logger.info(f"�� Розміщуємо {orders_count} DCA ордерів в діапазоні {range_percent}%...")

        # Розраховуємо ціни для DCA ордерів
        dca_prices = calculate_dca_prices(current_price, range_percent, orders_count, side)

        for i, order_price in enumerate(dca_prices):
            try:
                # Розраховуємо кількість
                qty = calculate_quantity(
                    config['limit_orders_amount'] / orders_count,
                    order_price
                )

                # Розміщуємо ордер
                order = self.session.place_order(
                    category="linear",
                    symbol=api_symbol,
                    side=api_side,
                    orderType="Limit",
                    qty=str(qty),
                    price=str(order_price),
                    timeInForce="GTC"
                )

                self.logger.info(f"✅ DCA ордер {i+1}: {format_price(order_price)} ({format_quantity(qty)})")

            except Exception as e:
                self.logger.error(f"❌ Помилка DCA ордера {i+1}: {e}")

    def monitor_positions(self, api_symbol):
        """
        Моніторинг поточних позицій

        Перевіряє статус позицій та виконаних ордерів,
        при необхідності перераховує TP ордери.

        Args:
            api_symbol (str): Символ для API (наприклад: 'BTCUSDT')
        """
        try:
            # Отримуємо поточні позиції
            positions = self.session.get_positions(
                category="linear",
                symbol=api_symbol
            )

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    self.logger.info(f"📊 Позиція активна: {format_quantity(float(position_list[0]['size']))}")

                    # Перевіряємо виконані ордери
                    self.check_executed_orders(api_symbol)
                else:
                    self.logger.info("�� Позиція не знайдена")
            else:
                self.logger.error(f"❌ Помилка отримання позицій: {positions}")

        except Exception as e:
            self.logger.error(f"❌ Помилка моніторингу: {e}")

    def check_executed_orders(self, api_symbol):
        """
        Перевірка виконаних ордерів

        Перевіряє чи є нові виконані ордери та при необхідності
        перераховує середню ціну та TP ордери.

        Args:
            api_symbol (str): Символ для API
        """
        try:
            # Отримуємо активні ордери
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )

            if orders['retCode'] == 0:
                order_list = orders['result']['list']
                self.logger.info(f"📋 Активних ордерів: {len(order_list)}")

                # Перевіряємо чи є виконані ордери
                for order in order_list:
                    if order['orderStatus'] == 'Filled':
                        self.logger.info(f"✅ Ордер виконано: {order['orderId']}")

                        # Перераховуємо середню ціну та TP ордери
                        self.recalculate_tp_orders(api_symbol)

        except Exception as e:
            self.logger.error(f"❌ Помилка перевірки ордерів: {e}")

    def get_current_position_info(self, symbol):
        """
        Отримання інформації про поточну позицію

        Args:
            symbol (str): Символ торгівельної пари

        Returns:
            dict or None: Інформація про позицію або None
        """
        try:
            api_symbol = get_api_symbol(symbol)
            positions = self.session.get_positions(
                category="linear",
                symbol=api_symbol
            )

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    return position_list[0]
            return None

        except Exception as e:
            self.logger.error(f"❌ Помилка отримання позиції: {e}")
            return None

    def calculate_new_avg_price(self, symbol):
        """
        Розрахунок нової середньої ціни позиції

        Args:
            symbol (str): Символ торгівельної пари

        Returns:
            float or None: Нова середня ціна або None
        """
        try:
            position_info = self.get_current_position_info(symbol)
            if position_info:
                avg_price = float(position_info['avgPrice'])
                self.logger.info(f"📊 Нова середня ціна: {format_price(avg_price)}")
                return avg_price
            return None

        except Exception as e:
            self.logger.error(f"❌ Помилка розрахунку середньої ціни: {e}")
            return None

    def cancel_tp_orders(self, api_symbol):
        """
        Скасування всіх TP ордерів

        Args:
            api_symbol (str): Символ для API
        """
        try:
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )

            if orders['retCode'] == 0:
                order_list = orders['result']['list']
                for order in order_list:
                    if order['orderType'] == 'Limit':
                        self.session.cancel_order(
                            category="linear",
                            symbol=api_symbol,
                            orderId=order['orderId']
                        )
                        self.logger.info(f"❌ Скасовано TP ордер: {order['orderId']}")

        except Exception as e:
            self.logger.error(f"❌ Помилка скасування TP ордерів: {e}")

    def recalculate_tp_orders(self, api_symbol):
        """
        Перерахунок та перевиставлення TP ордерів

        Скасовує старі TP ордери та створює нові на основі
        оновленої середньої ціни позиції.

        Args:
            api_symbol (str): Символ для API
        """
        try:
            # Скасовуємо старі TP ордери
            self.cancel_tp_orders(api_symbol)

            # Отримуємо нову середню ціну
            new_avg_price = self.calculate_new_avg_price(api_symbol.replace('USDT', '/USDT'))
            if not new_avg_price:
                return

            # Перевиставляємо TP ордери з новою ціною
            self.place_tp_orders(self.config, new_avg_price)

        except Exception as e:
            self.logger.error(f"❌ Помилка перерахунку TP ордерів: {e}")

    # Методи для веб-інтерфейсу
    def get_status(self):
        """
        Отримання статусу движка для веб-інтерфейсу

        Returns:
            dict: Статус движка з інформацією про роботу
        """
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'config': self.config,
            'uptime': time.time() - self.start_time if self.start_time else 0
        }

    def get_positions(self):
        """
        Отримання поточних позицій

        Returns:
            list: Список активних позицій
        """
        if not self.config:
            return []

        api_symbol = get_api_symbol(self.config['symbol'])
        return self.get_current_position_info(self.config['symbol'])

    def get_orders(self):
        """
        Отримання активних ордерів

        Returns:
            list: Список активних ордерів
        """
        if not self.config:
            return []

        api_symbol = get_api_symbol(self.config['symbol'])
        try:
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )
            if orders['retCode'] == 0:
                return orders['result']['list']
            return []
        except Exception as e:
            self.logger.error(f"❌ Помилка отримання ордерів: {e}")
            return []

    def close_all_positions(self):
        """
        Закриття всіх відкритих позицій

        Закриває всі активні позиції market ордерами
        та скасовує всі активні ордери.
        """
        if not self.config:
            self.logger.warning("⚠️ Немає конфігурації для закриття позицій")
            return

        try:
            api_symbol = get_api_symbol(self.config['symbol'])
            side = self.config['side']

            # Отримуємо поточні позиції
            positions = self.session.get_positions(
                category="linear",
                symbol=api_symbol
            )

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    position_size = float(position_list[0]['size'])

                    # Визначаємо сторону для закриття
                    close_side = "Buy" if side == "short" else "Sell"

                    self.logger.info(f"🔄 Закриваємо позицію: {format_quantity(position_size)}")

                    # Закриваємо позицію market ордером
                    close_order = self.session.place_order(
                        category="linear",
                        symbol=api_symbol,
                        side=close_side,
                        orderType="Market",
                        qty=str(position_size),
                        timeInForce="IOC"
                    )

                    if close_order['retCode'] == 0:
                        self.logger.info("✅ Позиція успішно закрита")
                    else:
                        self.logger.error(f"❌ Помилка закриття позиції: {close_order}")
                else:
                    self.logger.info("ℹ️ Немає активних позицій для закриття")

            # Скасовуємо всі активні ордери
            self.cancel_all_orders(api_symbol)

        except Exception as e:
            self.logger.error(f"❌ Помилка закриття позицій: {e}")

    def cancel_all_orders(self, api_symbol):
        """
        Скасування всіх активних ордерів

        Args:
            api_symbol (str): Символ для API
        """
        try:
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )

            if orders['retCode'] == 0:
                order_list = orders['result']['list']
                if order_list:
                    self.logger.info(f"🔄 Скасовуємо {len(order_list)} активних ордерів...")

                    for order in order_list:
                        try:
                            self.session.cancel_order(
                                category="linear",
                                symbol=api_symbol,
                                orderId=order['orderId']
                            )
                            self.logger.info(f"❌ Скасовано ордер: {order['orderId']}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Помилка скасування ордера {order['orderId']}: {e}")
                else:
                    self.logger.info("ℹ️ Немає активних ордерів для скасування")
            else:
                self.logger.error(f"❌ Помилка отримання ордерів: {orders}")

        except Exception as e:
            self.logger.error(f"❌ Помилка скасування ордерів: {e}")
