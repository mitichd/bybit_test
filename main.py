"""
Головний файл для запуску трейдингового движка
"""

from trading_engine import TradingEngine
import sys


def main():
    """Головна функція"""
    print("🚀 Запуск трейдингового движка...")

    try:
        # Створюємо екземпляр движка
        engine = TradingEngine()

        # Запускаємо торгівлю
        engine.start()

    except KeyboardInterrupt:
        print("\n🛑 Отримано сигнал зупинки...")
        engine.stop()
        print("✅ Движок зупинено")

    except Exception as e:
        print(f"❌ Критична помилка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
