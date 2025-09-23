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
    """

    def __init__(self):
        """Ініціалізація трейдингового движка"""
        self.logger = setup_logging()
        load_dotenv()
        self._connect_to_exchange()

        self.is_running = False
        self.config = None
        self.start_time = None
        self.last_position_size = 0

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _connect_to_exchange(self):
        """Підключення до Bybit API"""
        try:
            self.session = HTTP(
                testnet=False,
                demo=True,
                api_key=os.getenv('BYBIT_API_KEY'),
                api_secret=os.getenv('BYBIT_API_SECRET')
            )
            self.logger.info("🚀 Трейдинговий движок запущено!")
            self.logger.info("📊 Підключення до Bybit Demo успішне!")
        except Exception as e:
            self.logger.error(f"❌ Помилка підключення: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Обробка сигналів для graceful shutdown"""
        self.logger.info(f"🛑 Отримано сигнал {signum}. Закриваємо позиції...")
        self.stop()
        sys.exit(0)

    def load_config(self):
        """Завантаження конфігурації з JSON файлу"""
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
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
        """Запуск торгівлі"""
        if self.is_running:
            self.logger.warning("⚠️ Движок вже працює")
            return

        if not self.load_config():
            return

        self.is_running = True
        self.start_time = time.time()
        self._run_trading_loop()

    def stop(self):
        """Зупинка торгівлі з закриттям позицій"""
        if not self.is_running:
            self.logger.warning("⚠️ Движок не працює")
            return

        self.logger.info("🛑 Зупиняємо торгівлю...")
        self.close_all_positions()
        self.is_running = False
        self.logger.info("⏹️ Торгівля зупинена")

    def _run_trading_loop(self):
        """Основний цикл торгівлі"""
        self.logger.info("\n�� ЗАПУСК ТРЕЙДИНГОВОГО ДВИЖКА")
        self.logger.info("=" * 50)

        current_price = self.get_current_price(self.config['symbol'])
        if not current_price:
            return

        order = self.open_position(self.config)
        if not order:
            return

        self.place_tp_orders(self.config, current_price)
        self.place_dca_orders(self.config, current_price)

        self.logger.info("\n📊 Починаємо моніторинг...")
        api_symbol = get_api_symbol(self.config['symbol'])

        while self.is_running:
            self.monitor_positions(api_symbol)
            time.sleep(TradingConstants.MONITORING_INTERVAL)

    def get_current_price(self, symbol):
        """Отримання поточної ціни активу"""
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
        """Відкриття позиції"""
        symbol = config['symbol']
        side = config['side']
        amount = config['market_order_amount']
        leverage = config['leverage']

        api_side = get_api_side(side)
        api_symbol = get_api_symbol(symbol)

        self.logger.info(f"�� Відкриваємо позицію: {side} ${amount} {symbol} (x{leverage})")

        try:
            # Встановлюємо leverage
            try:
                self.session.set_leverage(
                    category="linear",
                    symbol=api_symbol,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage)
                )
                self.logger.info(f"✅ Leverage встановлено: {leverage}x")
            except Exception as leverage_error:
                if "110043" in str(leverage_error):
                    self.logger.info(f"ℹ️ Leverage вже встановлений: {leverage}x")
                else:
                    self.logger.warning(f"⚠️ Помилка leverage: {leverage_error}")

            current_price = self.get_current_price(symbol)
            if not current_price:
                return None

            qty = calculate_quantity(amount, current_price)
            self.logger.info(f"💰 Сума: ${amount}, Ціна: {format_price(current_price)}, Кількість: {format_quantity(qty)}")

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
        """Розміщення TP ордерів"""
        symbol = config['symbol']
        side = config['side']
        tp_orders = config['tp_orders']

        api_symbol = get_api_symbol(symbol)
        api_side = get_tp_side(side)

        self.logger.info(f"🎯 Розміщуємо {len(tp_orders)} TP ордерів...")

        for i, tp_order in enumerate(tp_orders):
            try:
                tp_price = calculate_tp_price(current_price, tp_order['price_percent'], side)
                qty = calculate_quantity(
                    (tp_order['quantity_percent'] / 100) * config['market_order_amount'],
                    current_price
                )

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
        """Розміщення DCA ордерів"""
        symbol = config['symbol']
        side = config['side']
        limit_orders = config['limit_orders']

        api_symbol = get_api_symbol(symbol)
        api_side = get_api_side(side)

        range_percent = limit_orders['range_percent']
        orders_count = limit_orders['orders_count']

        self.logger.info(f"📊 Розміщуємо {orders_count} DCA ордерів в діапазоні {range_percent}%...")

        dca_prices = calculate_dca_prices(current_price, range_percent, orders_count, side)

        for i, order_price in enumerate(dca_prices):
            try:
                qty = calculate_quantity(
                    config['limit_orders_amount'] / orders_count,
                    order_price
                )

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
        """Моніторинг поточних позицій"""
        try:
            positions = self.session.get_positions(category="linear", symbol=api_symbol)

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    current_size = float(position_list[0]['size'])
                    self.logger.info(f"📊 Позиція активна: {format_quantity(current_size)}")

                    # Перевіряємо чи збільшився розмір позиції
                    if current_size > self.last_position_size and self.last_position_size > 0:
                        self.logger.info("🔄 DCA ордер виконався! Перераховуємо TP ордери...")
                        self.recalculate_tp_orders(api_symbol)

                    self.last_position_size = current_size

                    # Показуємо активні ордери
                    orders = self.session.get_open_orders(category="linear", symbol=api_symbol)
                    if orders['retCode'] == 0:
                        order_list = orders['result']['list']
                        self.logger.info(f"📋 Активних ордерів: {len(order_list)}")
                else:
                    self.logger.info("�� Позиція не знайдена")
                    self.last_position_size = 0
            else:
                self.logger.error(f"❌ Помилка отримання позицій: {positions}")

        except Exception as e:
            self.logger.error(f"❌ Помилка моніторингу: {e}")

    def recalculate_tp_orders(self, api_symbol):
        """Перерахунок TP ордерів"""
        try:
            self.cancel_tp_orders(api_symbol)
            new_avg_price = self.calculate_new_avg_price(self.config['symbol'])
            if new_avg_price:
                self.place_tp_orders(self.config, new_avg_price)
        except Exception as e:
            self.logger.error(f"❌ Помилка перерахунку TP ордерів: {e}")

    def calculate_new_avg_price(self, symbol):
        """Розрахунок нової середньої ціни"""
        try:
            api_symbol = get_api_symbol(symbol)
            positions = self.session.get_positions(category="linear", symbol=api_symbol)

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    avg_price = float(position_list[0]['avgPrice'])
                    self.logger.info(f"📊 Нова середня ціна: {format_price(avg_price)}")
                    return avg_price
            return None
        except Exception as e:
            self.logger.error(f"❌ Помилка розрахунку середньої ціни: {e}")
            return None

    def cancel_tp_orders(self, api_symbol):
        """Скасування всіх Limit ордерів (TP + DCA)"""
        try:
            orders = self.session.get_open_orders(category="linear", symbol=api_symbol)
            if orders['retCode'] == 0:
                order_list = orders['result']['list']
                for order in order_list:
                    if order['orderType'] == 'Limit':
                        self.session.cancel_order(
                            category="linear",
                            symbol=api_symbol,
                            orderId=order['orderId']
                        )
                        self.logger.info(f"❌ Скасовано ордер: {order['orderId']}")
        except Exception as e:
            self.logger.error(f"❌ Помилка скасування ордерів: {e}")

    def close_all_positions(self):
        """Закриття всіх позицій"""
        if not self.config:
            return

        try:
            api_symbol = get_api_symbol(self.config['symbol'])
            side = self.config['side']

            positions = self.session.get_positions(category="linear", symbol=api_symbol)

            if positions['retCode'] == 0:
                position_list = positions['result']['list']
                if position_list and float(position_list[0]['size']) > 0:
                    position_size = float(position_list[0]['size'])
                    close_side = "Buy" if side == "short" else "Sell"

                    self.logger.info(f"🔄 Закриваємо позицію: {format_quantity(position_size)}")

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

            self.cancel_all_orders(api_symbol)

        except Exception as e:
            self.logger.error(f"❌ Помилка закриття позицій: {e}")

    def cancel_all_orders(self, api_symbol):
        """Скасування всіх ордерів"""
        try:
            orders = self.session.get_open_orders(category="linear", symbol=api_symbol)

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
        except Exception as e:
            self.logger.error(f"❌ Помилка скасування ордерів: {e}")

    # Методи для веб-інтерфейсу
    def get_status(self):
        """Отримання статусу движка"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'config': self.config,
            'uptime': time.time() - self.start_time if self.start_time else 0
        }

    def get_positions(self):
        """Отримання поточних позицій"""
        if not self.config:
            return []
        api_symbol = get_api_symbol(self.config['symbol'])
        positions = self.session.get_positions(category="linear", symbol=api_symbol)
        if positions['retCode'] == 0:
            return positions['result']['list']
        return []

    def get_orders(self):
        """Отримання активних ордерів"""
        if not self.config:
            return []
        api_symbol = get_api_symbol(self.config['symbol'])
        orders = self.session.get_open_orders(category="linear", symbol=api_symbol)
        if orders['retCode'] == 0:
            return orders['result']['list']
        return []
