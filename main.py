import os
import json
import time
from dotenv import load_dotenv
from pybit.unified_trading import HTTP


class SimpleTradingEngine:
    def __init__(self):
        # Завантажуємо змінні з .env
        load_dotenv()

        # Підключення до Bybit Demo
        self.session = HTTP(
            testnet=False,
            demo=True,
            api_key=os.getenv('BYBIT_API_KEY'),
            api_secret=os.getenv('BYBIT_API_SECRET')
        )

        print("🚀 Трейдинговий движок запущено!")
        print("📊 Підключення до Bybit Demo успішне!")

    def load_config(self):
        """Завантаження конфігурації з JSON файлу"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            print(f"✅ Конфігурація завантажена: {config['symbol']}")
            return config
        except Exception as e:
            print(f"❌ Помилка завантаження конфігурації: {e}")
            return None

    def get_current_price(self, symbol):
        """Отримання поточної ціни"""
        try:
            # Конвертуємо BTC/USDT в BTCUSDT для API
            api_symbol = symbol.replace('/', '')
            ticker = self.session.get_tickers(category="linear", symbol=api_symbol)
            price = float(ticker['result']['list'][0]['lastPrice'])
            print(f"📈 Поточна ціна {symbol}: ${price:,.2f}")
            return price
        except Exception as e:
            print(f"❌ Помилка отримання ціни: {e}")
            return None

    def open_position(self, config):
        """Відкриття позиції"""
        symbol = config['symbol']
        side = config['side']
        amount = config['market_order_amount']
        leverage = config['leverage']

        # Конвертуємо side
        api_side = "Sell" if side == "short" else "Buy"
        api_symbol = symbol.replace('/', '')

        print(f" Відкриваємо позицію: {side} ${amount} {symbol} (x{leverage})")

        try:
            # Спробуємо встановити leverage
            try:
                self.session.set_leverage(
                    category="linear",
                    symbol=api_symbol,
                    buyLeverage=str(leverage),
                    sellLeverage=str(leverage)
                )
                print(f"✅ Leverage встановлено: {leverage}x")
            except Exception as leverage_error:
                # Ігноруємо помилку leverage - він вже встановлений
                if "110043" in str(leverage_error):
                    print(f"ℹ️ Leverage вже встановлений: {leverage}x")
                else:
                    print(f"⚠️ Помилка leverage: {leverage_error}")

            # Отримуємо поточну ціну для розрахунку кількості
            current_price = self.get_current_price(symbol)
            if not current_price:
                return None

            # Розраховуємо кількість контрактів
            qty = amount / current_price

            # Округляємо до 3 знаків після коми (мінімум для BTCUSDT)
            qty = round(qty, 3)

            # Перевіряємо мінімальну кількість
            min_qty = 0.001  # Мінімальна кількість для BTCUSDT
            if qty < min_qty:
                print(f"⚠️ Кількість {qty} менше мінімальної {min_qty}")
                qty = min_qty
                print(f"ℹ️ Встановлюємо мінімальну кількість: {qty}")

            print(f"💰 Сума: ${amount}, Ціна: ${current_price:,.2f}, Кількість: {qty} BTC")

            # Відкриваємо позицію
            order = self.session.place_order(
                category="linear",
                symbol=api_symbol,
                side=api_side,
                orderType="Market",
                qty=str(qty),  # Передаємо округлену кількість
                timeInForce="IOC"
            )

            print(f"✅ Позиція відкрита: {order}")
            return order

        except Exception as e:
            print(f"❌ Помилка відкриття позиції: {e}")
            return None

    def place_tp_orders(self, config, avg_price):
        """Постановка TP ордерів"""
        symbol = config['symbol']
        side = config['side']
        total_amount = config['market_order_amount']

        # Конвертуємо side
        api_side = "Buy" if side == "short" else "Sell"
        api_symbol = symbol.replace('/', '')

        print(f"🎯 Ставимо TP ордери для {symbol}...")

        for i, tp in enumerate(config['tp_orders']):
            tp_price = avg_price * (1 + tp['price_percent'] / 100)
            tp_amount = total_amount * (tp['quantity_percent'] / 100)
            tp_qty = tp_amount / avg_price

            # Округляємо до 3 знаків після коми
            tp_qty = round(tp_qty, 3)

            # Перевіряємо мінімальну кількість
            min_qty = 0.001
            if tp_qty < min_qty:
                tp_qty = min_qty

            print(f"  TP {i + 1}: {tp['price_percent']}% = ${tp_price:,.2f} ({tp_qty} BTC)")

            try:
                self.session.place_order(
                    category="linear",
                    symbol=api_symbol,
                    side=api_side,
                    orderType="Limit",
                    qty=str(tp_qty),
                    price=str(tp_price)
                )
                print(f"  ✅ TP {i + 1} поставлено")
            except Exception as e:
                print(f"  ❌ Помилка TP {i + 1}: {e}")

    def place_dca_orders(self, config, current_price):
        """Постановка DCA ордерів"""
        symbol = config['symbol']
        side = config['side']
        range_percent = config['limit_orders']['range_percent']
        orders_count = config['limit_orders']['orders_count']
        total_amount = config['limit_orders_amount']

        # Конвертуємо side
        api_side = "Sell" if side == "short" else "Buy"
        api_symbol = symbol.replace('/', '')

        print(f" Ставимо DCA ордери для {symbol}...")
        print(f"  Діапазон: {range_percent}%, Кількість: {orders_count}, Сума: ${total_amount}")

        # Розраховуємо ціни та суми
        price_step = (current_price * range_percent / 100) / orders_count
        amount_per_order = total_amount / orders_count

        for i in range(orders_count):
            if side == "short":
                dca_price = current_price + (price_step * (i + 1))
            else:
                dca_price = current_price - (price_step * (i + 1))

            dca_qty = amount_per_order / dca_price

            # Округляємо до 3 знаків після коми
            dca_qty = round(dca_qty, 3)

            # Перевіряємо мінімальну кількість
            min_qty = 0.001
            if dca_qty < min_qty:
                dca_qty = min_qty

            print(f"  DCA {i + 1}: ${dca_price:,.2f} ({dca_qty} BTC)")

            try:
                self.session.place_order(
                    category="linear",
                    symbol=api_symbol,
                    side=api_side,
                    orderType="Limit",
                    qty=str(dca_qty),
                    price=str(dca_price)
                )
                print(f"  ✅ DCA {i + 1} поставлено")
            except Exception as e:
                print(f"  ❌ Помилка DCA {i + 1}: {e}")

    def monitor_positions(self, symbol):
        """Моніторинг з DCA логікою"""
        try:
            api_symbol = symbol.replace('/', '')

            # Отримуємо поточну позицію
            current_position = self.get_current_position_info(symbol)

            if current_position:
                print(f"\n📊 ПОЗИЦІЯ: {current_position['size']} BTC")
                print(f"💰 Середня ціна: ${current_position['avg_price']:,.2f}")
                print(f"📈 PnL: ${current_position['unrealised_pnl']:,.2f}")

                # Перевіряємо виконані ордери
                executed_orders = self.check_executed_orders(symbol)

                if executed_orders:
                    print(f"🔄 Виконано {len(executed_orders)} ордерів")

                    # Розраховуємо нову середню ціну
                    new_avg_price = self.calculate_new_avg_price(current_position, executed_orders)

                    if new_avg_price != current_position['avg_price']:
                        print(
                            f"�� Середня ціна змінилася: ${current_position['avg_price']:,.2f} → ${new_avg_price:,.2f}")

                        # Перераховуємо TP ордери
                        self.recalculate_tp_orders(self.config, new_avg_price)

            return current_position

        except Exception as e:
            print(f"❌ Помилка моніторингу: {e}")
            return None

    def check_executed_orders(self, symbol):
        """Перевірка виконаних ордерів"""
        try:
            api_symbol = symbol.replace('/', '')

            # Отримуємо всі ордери
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )

            # Отримуємо історію ордерів
            order_history = self.session.get_order_history(
                category="linear",
                symbol=api_symbol,
                limit=50
            )

            executed_orders = []

            # Перевіряємо виконані ордери
            for order in order_history['result']['list']:
                if order['orderStatus'] == 'Filled':
                    executed_orders.append(order)

            return executed_orders

        except Exception as e:
            print(f"❌ Помилка перевірки ордерів: {e}")
            return []

    def get_current_position_info(self, symbol):
        """Отримання поточної інформації про позицію"""
        try:
            api_symbol = symbol.replace('/', '')
            positions = self.session.get_positions(category="linear", symbol=api_symbol)

            for pos in positions['result']['list']:
                if float(pos['size']) > 0:
                    return {
                        'size': float(pos['size']),
                        'avg_price': float(pos['avgPrice']),
                        'unrealised_pnl': float(pos['unrealisedPnl'])
                    }
            return None

        except Exception as e:
            print(f"❌ Помилка отримання позиції: {e}")
            return None

    def calculate_new_avg_price(self, current_position, executed_orders):
        """Розрахунок нової середньої ціни"""
        if not current_position or not executed_orders:
            return current_position['avg_price'] if current_position else 0

        total_size = current_position['size']
        total_value = current_position['size'] * current_position['avg_price']

        # Додаємо виконані ордери
        for order in executed_orders:
            order_size = float(order['qty'])
            order_price = float(order['avgPrice'])

            total_size += order_size
            total_value += order_size * order_price

        if total_size > 0:
            new_avg_price = total_value / total_size
            print(f"🔄 Нова середня ціна: ${new_avg_price:,.2f}")
            return new_avg_price

        return current_position['avg_price']

    def cancel_tp_orders(self, symbol):
        """Скасування всіх TP ордерів"""
        try:
            api_symbol = symbol.replace('/', '')

            # Отримуємо всі відкриті ордери
            orders = self.session.get_open_orders(
                category="linear",
                symbol=api_symbol
            )

            # Скасовуємо TP ордери (Limit ордери)
            for order in orders['result']['list']:
                if order['orderType'] == 'Limit':
                    self.session.cancel_order(
                        category="linear",
                        symbol=api_symbol,
                        orderId=order['orderId']
                    )
                    print(f"🗑️ Скасовано TP ордер: {order['orderId']}")

            return True

        except Exception as e:
            print(f"❌ Помилка скасування TP ордерів: {e}")
            return False

    def recalculate_tp_orders(self, config, new_avg_price):
        """Перерахунок TP ордерів з новою середньою ціною"""
        symbol = config['symbol']
        side = config['side']
        total_amount = config['market_order_amount']

        # Конвертуємо side
        api_side = "Buy" if side == "short" else "Sell"
        api_symbol = symbol.replace('/', '')

        print(f"🔄 Перераховуємо TP ордери з новою ціною: ${new_avg_price:,.2f}")

        # Скасовуємо старі TP ордери
        self.cancel_tp_orders(symbol)

        # Ставимо нові TP ордери
        for i, tp in enumerate(config['tp_orders']):
            tp_price = new_avg_price * (1 + tp['price_percent'] / 100)
            tp_amount = total_amount * (tp['quantity_percent'] / 100)
            tp_qty = tp_amount / new_avg_price
            tp_qty = round(tp_qty, 3)

            # Перевіряємо мінімальну кількість
            min_qty = 0.001
            if tp_qty < min_qty:
                tp_qty = min_qty

            print(f"  TP {i + 1}: {tp['price_percent']}% = ${tp_price:,.2f} ({tp_qty} BTC)")

            try:
                self.session.place_order(
                    category="linear",
                    symbol=api_symbol,
                    side=api_side,
                    orderType="Limit",
                    qty=str(tp_qty),
                    price=str(tp_price)
                )
                print(f"  ✅ TP {i + 1} перераховано")
            except Exception as e:
                print(f"  ❌ Помилка TP {i + 1}: {e}")

    def run(self):
        """Основний цикл роботи"""
        print("\n ЗАПУСК ТРЕЙДИНГОВОГО ДВИЖКА")
        print("=" * 50)

        # Завантажуємо конфігурацію
        config = self.load_config()
        if not config:
            return

        # Зберігаємо конфігурацію для використання в моніторингу
        self.config = config

        # Отримуємо поточну ціну
        current_price = self.get_current_price(config['symbol'])
        if not current_price:
            return

        # Відкриваємо позицію
        order = self.open_position(config)
        if not order:
            return

        # Ставимо TP ордери
        self.place_tp_orders(config, current_price)

        # Ставимо DCA ордери
        self.place_dca_orders(config, current_price)

        # Моніторинг з DCA логікою
        print("\n Починаємо моніторинг з DCA логікою...")
        api_symbol = config['symbol'].replace('/', '')

        while True:
            self.monitor_positions(api_symbol)
            time.sleep(10)


if __name__ == "__main__":
    engine = SimpleTradingEngine()
    engine.run()
