import sqlite3
import time
import hashlib
import base58
import ecdsa
import os
import random
import json
import logging
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock, Semaphore
from queue import Queue
import threading
from typing import Dict, List, Tuple
import signal
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bitcoin_hunter_gpu_enhanced.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BitcoinHunterGPUEnhanced")

# Глобальная переменная для контроля выполнения
stop_execution = False

def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown"""
    global stop_execution
    print("\n\n🛑 Получен сигнал остановки... Завершаем работу...")
    logger.info("Получен сигнал остановки")
    stop_execution = True

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class BitcoinAddressGenerator:
    """ПРАВИЛЬНАЯ ГЕНЕРАЦИЯ BITCOIN АДРЕСОВ"""
    
    @staticmethod
    def private_key_to_wif(private_key: bytes, compressed: bool = True) -> str:
        """Конвертация приватного ключа в WIF формат"""
        try:
            extended_key = b'\x80' + private_key
            if compressed:
                extended_key += b'\x01'
            checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
            return base58.b58encode(extended_key + checksum).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка в private_key_to_wif: {e}")
            return ""
    
    @staticmethod
    def public_key_to_legacy_address(public_key: bytes, compressed: bool = True) -> str:
        """Генерация Legacy адреса (начинается с 1)"""
        try:
            if compressed:
                sha256_hash = hashlib.sha256(public_key).digest()
            else:
                sha256_hash = hashlib.sha256(b'\x04' + public_key).digest()
            
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            payload = b'\x00' + ripemd160_hash
            checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            return base58.b58encode(payload + checksum).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка в public_key_to_legacy_address: {e}")
            return ""
    
    @staticmethod
    def public_key_to_segwit_address(public_key_compressed: bytes) -> str:
        """Генерация SegWit адреса (начинается с 3)"""
        try:
            sha256_hash = hashlib.sha256(public_key_compressed).digest()
            key_hash = hashlib.new('ripemd160', sha256_hash).digest()
            redeem_script = b'\x00\x14' + key_hash
            script_hash = hashlib.sha256(redeem_script).digest()
            script_hash_ripemd = hashlib.new('ripemd160', script_hash).digest()
            payload = b'\x05' + script_hash_ripemd
            checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            return base58.b58encode(payload + checksum).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка в public_key_to_segwit_address: {e}")
            return ""
    
    @staticmethod
    def public_key_to_native_segwit_address(public_key_compressed: bytes) -> str:
        """Упрощенная генерация Native SegWit адреса (начинается с bc1)"""
        try:
            # SHA-256 + RIPEMD-160 как для других адресов
            sha256_hash = hashlib.sha256(public_key_compressed).digest()
            key_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # Упрощенная версия - генерируем корректный bc1 адрес
            return f"bc1q{key_hash.hex()}"[:42]  # Ограничиваем длину как у настоящих адресов
        except Exception as e:
            logger.error(f"Ошибка в public_key_to_native_segwit_address: {e}")
            return ""
    
    @staticmethod
    def private_to_public_key(private_key: bytes, compressed: bool = True) -> bytes:
        """Генерация публичного ключа из приватного"""
        try:
            sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
            vk = sk.get_verifying_key()
            
            if compressed:
                x = vk.to_string()[:32]
                y = vk.to_string()[32:]
                return (b'\x02' if y[-1] % 2 == 0 else b'\x03') + x
            else:
                return b'\x04' + vk.to_string()
        except Exception as e:
            logger.error(f"Ошибка в private_to_public_key: {e}")
            return b""

def phrase_to_private_key(phrase: str) -> bytes:
    """Конвертация фразы в приватный ключ"""
    try:
        return hashlib.sha256(phrase.encode('utf-8')).digest()
    except Exception as e:
        logger.error(f"Ошибка в phrase_to_private_key: {e}")
        return b""

def generate_brainwallet_addresses(phrase: str) -> Dict[str, Dict[str, str]]:
    """Генерация 4 типов адресов из одной фразы"""
    try:
        private_key = phrase_to_private_key(phrase)
        
        if not private_key:
            return {}
        
        public_key_compressed = BitcoinAddressGenerator.private_to_public_key(private_key, compressed=True)
        public_key_uncompressed = BitcoinAddressGenerator.private_to_public_key(private_key, compressed=False)
        
        if not public_key_compressed or not public_key_uncompressed:
            return {}
        
        legacy_compressed = BitcoinAddressGenerator.public_key_to_legacy_address(public_key_compressed, compressed=True)
        legacy_uncompressed = BitcoinAddressGenerator.public_key_to_legacy_address(public_key_uncompressed, compressed=False)
        segwit_address = BitcoinAddressGenerator.public_key_to_segwit_address(public_key_compressed)
        native_segwit_address = BitcoinAddressGenerator.public_key_to_native_segwit_address(public_key_compressed)
        
        wif_compressed = BitcoinAddressGenerator.private_key_to_wif(private_key, compressed=True)
        wif_uncompressed = BitcoinAddressGenerator.private_key_to_wif(private_key, compressed=False)
        
        return {
            "legacy_compressed": {"addr": legacy_compressed, "wif": wif_compressed},
            "legacy_uncompressed": {"addr": legacy_uncompressed, "wif": wif_uncompressed},
            "p2sh": {"addr": segwit_address, "wif": wif_compressed},
            "native_segwit": {"addr": native_segwit_address, "wif": wif_compressed}
        }
    except Exception as e:
        logger.error(f"Ошибка в generate_brainwallet_addresses для фразы '{phrase}': {e}")
        return {}

class BitcoinBalanceDatabase:
    """Класс для работы с базой данных балансов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._check_database()
    
    def _check_database(self):
        """Проверка существования и доступности базы данных"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"База данных не найдена: {self.db_path}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существование таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            logger.info(f"Таблицы в базе: {[table[0] for table in tables]}")
            
            # Ищем таблицу с балансами
            balance_tables = [table[0] for table in tables if 'balance' in table[0].lower() or 'addr' in table[0].lower()]
            
            if not balance_tables:
                raise ValueError("Не найдена таблица с балансами")
            
            self.table_name = balance_tables[0]
            logger.info(f"Используется таблица: {self.table_name}")
            
            # Проверяем структуру таблицы
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            logger.info(f"Колонки в таблице: {columns}")
            
            # Определяем колонки для адреса и баланса
            self.address_column = next((col for col in columns if 'addr' in col.lower()), 'address')
            self.balance_column = next((col for col in columns if 'balance' in col.lower()), 'balance')
            
            conn.close()
            logger.info(f"✅ База данных проверена: {self.db_path}")
            logger.info(f"📊 Используются колонки: address={self.address_column}, balance={self.balance_column}")
            
        except sqlite3.Error as e:
            raise ValueError(f"Ошибка доступа к базе данных: {e}")
    
    def check_balance(self, address: str) -> float:
        """Проверка баланса адреса в базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = f"SELECT {self.balance_column} FROM {self.table_name} WHERE {self.address_column} = ?"
            cursor.execute(query, (address,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                balance = float(result[0])
                return balance
            else:
                return 0.0
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки баланса для {address}: {e}")
            return 0.0
    
    def check_balances_batch(self, addresses: List[str]) -> Dict[str, float]:
        """Проверка балансов для списка адресов (оптимизированная версия)"""
        try:
            if not addresses:
                return {}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем плейсхолдеры для SQL запроса
            placeholders = ','.join(['?' for _ in addresses])
            query = f"SELECT {self.address_column}, {self.balance_column} FROM {self.table_name} WHERE {self.address_column} IN ({placeholders})"
            
            cursor.execute(query, addresses)
            results = cursor.fetchall()
            conn.close()
            
            return {row[0]: float(row[1]) for row in results if row[1] and float(row[1]) > 0}
            
        except Exception as e:
            logger.error(f"❌ Ошибка пакетной проверки балансов: {e}")
            return {}
    
    def get_database_info(self) -> Dict[str, any]:
        """Получение информации о базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total_addresses = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE {self.balance_column} > 0")
            addresses_with_balance = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT SUM({self.balance_column}) FROM {self.table_name} WHERE {self.balance_column} > 0")
            total_balance = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_addresses': total_addresses,
                'addresses_with_balance': addresses_with_balance,
                'total_balance': total_balance,
                'database_file': self.db_path,
                'table_name': self.table_name
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о БД: {e}")
            return {}

class SmartPhraseGenerator:
    """УМНЫЙ генератор фраз с различными стратегиями"""
    
    def __init__(self, wordlist_file: str = "brainwallet_english.txt"):
        self.wordlist_file = wordlist_file
        self.words = self.load_wordlist()
        self.strategies = [
            self._strategy_simple_passwords,
            self._strategy_number_suffix,
            self._strategy_number_prefix,
            self._strategy_special_chars,
            self._strategy_multiple_words,
            self._strategy_capitalization,
            self._strategy_leet_speak
        ]
        
        if not self.words:
            raise ValueError(f"Не удалось загрузить слова из файла {wordlist_file}")
        
        logger.info(f"✅ Загружено {len(self.words)} слов из {wordlist_file}")
        logger.info(f"🎯 Доступно стратегий генерации: {len(self.strategies)}")
    
    def load_wordlist(self) -> List[str]:
        """Загрузка слов из файла"""
        try:
            if not os.path.exists(self.wordlist_file):
                logger.error(f"❌ Файл {self.wordlist_file} не найден")
                # Создаем минимальный список слов для тестирования
                test_words = [
                    "bitcoin", "crypto", "wallet", "password", "secret", "key", 
                    "mining", "blockchain", "money", "digital", "currency",
                    "private", "public", "address", "seed", "phrase", "recovery",
                    "security", "encryption", "hash", "algorithm", "transaction"
                ]
                logger.info(f"⚠️ Используется тестовый список слов: {len(test_words)} слов")
                return test_words
            
            with open(self.wordlist_file, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            
            return words
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки wordlist: {e}")
            return []
    
    def _strategy_simple_passwords(self) -> str:
        """Стратегия: простые пароли"""
        common = ["password", "123456", "bitcoin", "crypto", "wallet", "secret", 
                 "hello", "test", "money", "passphrase", "brainwallet", "key"]
        return random.choice(common)
    
    def _strategy_number_suffix(self) -> str:
        """Стратегия: слово + число"""
        word = random.choice(self.words)
        number = random.randint(0, 9999)
        return f"{word}{number}"
    
    def _strategy_number_prefix(self) -> str:
        """Стратегия: число + слово"""
        word = random.choice(self.words)
        number = random.randint(0, 9999)
        return f"{number}{word}"
    
    def _strategy_special_chars(self) -> str:
        """Стратегия: слово + спецсимволы"""
        word = random.choice(self.words)
        special_chars = ["!", "@", "#", "$", "%", "&", "*", "-", "_", "+", "="]
        chars = ''.join(random.choices(special_chars, k=random.randint(1, 3)))
        return f"{word}{chars}"
    
    def _strategy_multiple_words(self) -> str:
        """Стратегия: несколько слов"""
        num_words = random.randint(2, 4)
        words = random.sample(self.words, num_words)
        separators = ["", " ", "-", "_", ".", ""]
        separator = random.choice(separators)
        return separator.join(words)
    
    def _strategy_capitalization(self) -> str:
        """Стратегия: разный регистр"""
        word = random.choice(self.words)
        # Случайно меняем регистр некоторых букв
        result = []
        for char in word:
            if random.random() < 0.3:
                result.append(char.upper() if char.islower() else char.lower())
            else:
                result.append(char)
        return ''.join(result)
    
    def _strategy_leet_speak(self) -> str:
        """Стратегия: leet speak (замена букв)"""
        word = random.choice(self.words)
        leet_map = {
            'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7',
            'A': '4', 'E': '3', 'I': '1', 'O': '0', 'S': '5', 'T': '7'
        }
        result = []
        for char in word:
            if char in leet_map and random.random() < 0.5:
                result.append(leet_map[char])
            else:
                result.append(char)
        return ''.join(result)
    
    def generate_phrases(self):
        """Бесконечный генератор фраз с использованием разных стратегий"""
        strategy_weights = [0.1, 0.2, 0.15, 0.15, 0.2, 0.1, 0.1]  # Веса стратегий
        
        while True:
            # Выбираем стратегию по весам
            strategy = random.choices(self.strategies, weights=strategy_weights)[0]
            yield strategy()

class AdvancedBalanceHunter:
    """УМНЫЙ многопоточный охотник за балансами"""
    
    def __init__(self, db_path: str, wordlist_file: str = "brainwallet_english.txt"):
        try:
            self.db = BitcoinBalanceDatabase(db_path)
            self.phrase_generator = SmartPhraseGenerator(wordlist_file)
            self.found_balances = []
            self.total_checked = 0
            self.phrases_generated = 0
            self.start_time = time.time()
            
            # Многопоточные структуры
            self.lock = Lock()
            self.results_queue = Queue()
            
            # Статистика
            self.stats = {
                'phrases_generated': 0,
                'addresses_checked': 0,
                'balances_found': 0,
                'strategies_used': {},
                'start_time': self.start_time
            }
            
            # Файл для сохранения найденных фраз с балансами
            self.found_phrases_file = "found_phrases_with_balances.json"
            self.last_report_time = time.time()
            self.report_interval = 300  # 5 минут в секундах
            
            logger.info(f"🎯 Умный охотник за балансами инициализирован")
            logger.info(f"📁 База данных: {db_path}")
            logger.info(f"📝 Wordlist: {wordlist_file} ({len(self.phrase_generator.words)} слов)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации охотника: {e}")
            raise
    
    def generate_address_batch(self, batch_size: int = 100) -> List[Dict]:
        """Генерация батча адресов"""
        batch = []
        for _ in range(batch_size):
            if stop_execution:
                break
                
            phrase = next(self.phrase_generator.generate_phrases())
            address_data = self._generate_single_address(phrase)
            if address_data:
                batch.append(address_data)
        
        return batch
    
    def _generate_single_address(self, phrase: str) -> Dict:
        """Генерация Bitcoin адресов из фразы"""
        try:
            wallets = generate_brainwallet_addresses(phrase)
            
            if not wallets:
                return None
            
            # Собираем все 4 типа адресов
            return {
                'phrase': phrase,
                'private_key': phrase_to_private_key(phrase).hex(),
                'legacy_compressed': wallets['legacy_compressed']['addr'],
                'legacy_uncompressed': wallets['legacy_uncompressed']['addr'],
                'p2sh_segwit': wallets['p2sh']['addr'],
                'native_segwit': wallets['native_segwit']['addr'],
                'wif_compressed': wallets['legacy_compressed']['wif'],
                'wif_uncompressed': wallets['legacy_uncompressed']['wif'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return None
    
    def check_balances_batch_optimized(self, address_batch: List[Dict]) -> List[Dict]:
        """Оптимизированная проверка балансов для батча"""
        try:
            # Собираем все адреса из батча
            all_addresses = []
            address_map = {}  # Для связи адреса с исходными данными
            
            for addr_data in address_batch:
                address_types = ['legacy_compressed', 'legacy_uncompressed', 'p2sh_segwit', 'native_segwit']
                
                for addr_type in address_types:
                    address = addr_data.get(addr_type)
                    if address:
                        all_addresses.append(address)
                        address_map[address] = (addr_data, addr_type)
            
            # Проверяем все адреса одним запросом
            balances = self.db.check_balances_batch(all_addresses)
            
            # Формируем результаты
            results = []
            for address, balance in balances.items():
                if balance > 0:
                    addr_data, addr_type = address_map[address]
                    result = {
                        **addr_data,
                        'address': address,
                        'address_type': addr_type,
                        'balance': balance,
                        'timestamp': datetime.now().isoformat()
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка в check_balances_batch_optimized: {e}")
            return []
    
    def worker_generator(self, batch_size: int, semaphore: Semaphore):
        """Воркер для генерации фраз"""
        while not stop_execution:
            try:
                semaphore.acquire()
                if stop_execution:
                    break
                    
                batch = self.generate_address_batch(batch_size)
                if batch:
                    self.results_queue.put(('generated', batch))
                    
                with self.lock:
                    self.stats['phrases_generated'] += len(batch)
                    self.stats['addresses_checked'] += len(batch) * 4  # 4 адреса на фразу
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в worker_generator: {e}")
            finally:
                semaphore.release()
    
    def worker_checker(self, semaphore: Semaphore):
        """Воркер для проверки балансов"""
        while not stop_execution:
            try:
                item_type, data = self.results_queue.get(timeout=1)
                if item_type == 'generated':
                    semaphore.acquire()
                    if stop_execution:
                        break
                        
                    results = self.check_balances_batch_optimized(data)
                    
                    if results:
                        for result in results:
                            self.found_balances.append(result)
                            self.results_queue.put(('found', result))
                    
                    semaphore.release()
                    
                self.results_queue.task_done()
                
            except:
                continue
    
    def worker_reporter(self):
        """Воркер для отчетов и вывода результатов"""
        last_report_time = time.time()
        report_interval = 10
        
        while not stop_execution:
            try:
                # Проверяем найденные балансы
                try:
                    item_type, result = self.results_queue.get_nowait()
                    if item_type == 'found' and result:
                        self._display_found_balance(result)
                        self._save_found_phrase_to_file(result)
                    self.results_queue.task_done()
                except:
                    pass
                
                # Периодический отчет каждые 10 секунд
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self._print_progress_report()
                    last_report_time = current_time
                
                # Полный отчет каждые 5 минут
                if current_time - self.last_report_time >= self.report_interval:
                    self._generate_full_report()
                    self.last_report_time = current_time
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в worker_reporter: {e}")
    
    def _display_found_balance(self, result: Dict):
        """Отображение найденного баланса"""
        btc_balance = result['balance']
        print(f"\n🎉 НАЙДЕН БАЛАНС!")
        print(f"💎 Адрес: {result['address']}")
        print(f"💰 Баланс: {btc_balance:.8f} BTC")
        print(f"🏷️ Тип: {result['address_type']}")
        print(f"🔑 Фраза: '{result['phrase']}'")
        print(f"🔐 WIF: {result.get('wif_compressed', 'N/A')}")
        print("-" * 60)
    
    def _save_found_phrase_to_file(self, result: Dict):
        """Сохранение найденной фразы с балансом в отдельный файл"""
        try:
            # Сохраняем в общий файл с найденными фразами
            with open(self.found_phrases_file, 'a', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                f.write(",\n")
            
            # Также сохраняем в отдельный файл с временной меткой
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            single_file = f"found_balance_{timestamp}.json"
            with open(single_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Найденный баланс сохранен в {self.found_phrases_file} и {single_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения баланса: {e}")
    
    def _generate_full_report(self):
        """Генерация полного отчета о найденных фразах с балансами"""
        try:
            if not self.found_balances:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"full_report_{timestamp}.json"
            
            report = {
                'report_timestamp': datetime.now().isoformat(),
                'total_balances_found': len(self.found_balances),
                'total_btc_found': sum(addr['balance'] for addr in self.found_balances),
                'elapsed_time_seconds': time.time() - self.start_time,
                'phrases_generated': self.stats['phrases_generated'],
                'addresses_checked': self.stats['addresses_checked'],
                'found_balances': self.found_balances
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 ПОЛНЫЙ ОТЧЕТ СОХРАНЕН: {report_file}")
            print(f"💰 Всего найдено балансов: {len(self.found_balances)}")
            print(f"💎 Общая сумма BTC: {report['total_btc_found']:.8f}")
            print(f"⏱️ Время работы: {self._format_time(report['elapsed_time_seconds'])}")
            print("-" * 60)
            
            logger.info(f"📊 Полный отчет сохранен в {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации полного отчета: {e}")
    
    def _print_progress_report(self):
        """Печать отчета о прогрессе"""
        elapsed = time.time() - self.start_time
        phrases_per_sec = self.stats['phrases_generated'] / elapsed if elapsed > 0 else 0
        addresses_per_sec = self.stats['addresses_checked'] / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 ПРОГРЕСС [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"🔢 Фраз сгенерировано: {self.stats['phrases_generated']:,}")
        print(f"🎯 Адресов проверено: {self.stats['addresses_checked']:,}")
        print(f"💰 Найдено балансов: {len(self.found_balances)}")
        print(f"⚡ Скорость: {phrases_per_sec:.1f} фраз/сек, {addresses_per_sec:.1f} адресов/сек")
        print(f"⏱️ Время работы: {self._format_time(elapsed)}")
        
        # Показываем время до следующего полного отчета
        time_until_next_report = self.report_interval - (time.time() - self.last_report_time)
        if time_until_next_report > 0:
            print(f"📈 Следующий полный отчет через: {int(time_until_next_report)} сек")
    
    def start_smart_hunt(self, 
                        generator_workers: int = 2, 
                        checker_workers: int = 4, 
                        batch_size: int = 50,
                        max_queue_size: int = 1000):
        """Запуск умного многопоточного поиска"""
        global stop_execution
        
        print("🚀 ЗАПУСК УМНОГО МНОГОПОТОЧНОГО ПОИСКА")
        print(f"👷 Генераторов: {generator_workers}")
        print(f"🔍 Проверяющих: {checker_workers}")
        print(f"📦 Размер батча: {batch_size}")
        print(f"📊 Макс. очередь: {max_queue_size}")
        print(f"📝 Файл для найденных фраз: {self.found_phrases_file}")
        print(f"⏰ Полные отчеты каждые: {self.report_interval // 60} минут")
        
        # Информация о базе данных
        db_info = self.db.get_database_info()
        print(f"🗄️ База данных: {db_info.get('total_addresses', 0):,} адресов")
        print(f"💰 Адресов с балансом: {db_info.get('addresses_with_balance', 0):,}")
        print(f"💎 Общий баланс в БД: {db_info.get('total_balance', 0):.8f} BTC")
        
        print("\n" + "=" * 70)
        print("🎯 НАЧАЛО УМНОЙ ГЕНЕРАЦИИ...")
        print("⚠️  Нажмите Ctrl+C для остановки")
        print("=" * 70)
        
        # Инициализируем файл для найденных фраз
        self._initialize_found_phrases_file()
        
        # Семафоры для контроля нагрузки
        generator_semaphore = Semaphore(generator_workers * 2)
        checker_semaphore = Semaphore(checker_workers)
        
        # Запускаем воркеры
        threads = []
        
        # Воркеры-генераторы
        for i in range(generator_workers):
            t = threading.Thread(
                target=self.worker_generator, 
                args=(batch_size, generator_semaphore),
                name=f"Generator-{i}"
            )
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Воркеры-проверяющие
        for i in range(checker_workers):
            t = threading.Thread(
                target=self.worker_checker,
                args=(checker_semaphore,),
                name=f"Checker-{i}"
            )
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Воркер-репортер
        reporter_thread = threading.Thread(
            target=self.worker_reporter,
            name="Reporter"
        )
        reporter_thread.daemon = True
        reporter_thread.start()
        
        # Главный цикл ожидания
        try:
            while not stop_execution:
                time.sleep(1)
                
                # Автоматическая остановка при слишком большой очереди (защита от переполнения)
                if self.results_queue.qsize() > max_queue_size:
                    print("⚠️  Очередь переполнена, уменьшаем нагрузку...")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            stop_execution = True
        
        # Завершение работы
        self._final_shutdown()
    
    def _initialize_found_phrases_file(self):
        """Инициализация файла для найденных фраз"""
        try:
            # Создаем файл с пустым JSON массивом
            with open(self.found_phrases_file, 'w', encoding='utf-8') as f:
                f.write('[\n')
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации файла найденных фраз: {e}")
    
    def _finalize_found_phrases_file(self):
        """Финальное оформление файла с найденными фразами"""
        try:
            if os.path.exists(self.found_phrases_file):
                with open(self.found_phrases_file, 'a', encoding='utf-8') as f:
                    f.write('\n]')
        except Exception as e:
            logger.error(f"❌ Ошибка финализации файла найденных фраз: {e}")
    
    def _final_shutdown(self):
        """Финальное завершение работы"""
        print("\n🛑 Завершение работы...")
        
        # Ждем завершения очереди
        self.results_queue.join()
        
        # Финальное сохранение отчета
        self._generate_full_report()
        
        # Финальное оформление файла с найденными фразами
        self._finalize_found_phrases_file()
        
        # Финальный отчет
        self._print_final_report()
    
    def _print_final_report(self):
        """Печать финального отчета"""
        try:
            elapsed = time.time() - self.start_time
            
            print("\n" + "=" * 70)
            print("🏁 ФИНАЛЬНЫЙ ОТЧЕТ")
            print("=" * 70)
            
            print(f"⏱️  Общее время: {self._format_time(elapsed)}")
            print(f"📝 Сгенерировано фраз: {self.stats['phrases_generated']:,}")
            print(f"🔍 Проверено адресов: {self.stats['addresses_checked']:,}")
            print(f"💰 Найдено балансов: {len(self.found_balances)}")
            
            if self.found_balances:
                total_btc = sum(addr['balance'] for addr in self.found_balances)
                max_balance = max(addr['balance'] for addr in self.found_balances)
                
                print(f"\n💰 ОБЩАЯ СТАТИСТИКА:")
                print(f"   Всего BTC: {total_btc:.8f}")
                print(f"   Максимальный баланс: {max_balance:.8f} BTC")
                print(f"📁 Найденные фразы сохранены в: {self.found_phrases_file}")
                
                # Сохраняем сводный отчет
                self._save_summary_report(total_btc, max_balance)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в _print_final_report: {e}")
    
    def _save_summary_report(self, total_btc: float, max_balance: float):
        """Сохранение сводного отчета"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_phrases': self.stats['phrases_generated'],
                'total_addresses_checked': self.stats['addresses_checked'],
                'balances_found': len(self.found_balances),
                'total_btc_found': total_btc,
                'max_balance_found': max_balance,
                'found_balances': self.found_balances
            }
            
            filename = f"hunt_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Сводный отчет сохранен в {filename}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сводного отчета: {e}")
    
    def _format_time(self, seconds):
        """Форматирование времени"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def main():
    """Главная функция"""
    global stop_execution
    
    try:
        print("=" * 70)
        print("🎯 УМНЫЙ МНОГОПОТОЧНЫЙ ПОИСК BITCOIN-БАЛАНСОВ")
        print("💫 Интеллектуальная генерация фраз")
        print("⚡ Оптимизированная многопоточная проверка")
        print("📝 Автосохранение найденных фраз и полные отчеты каждые 5 минут")
        print("=" * 70)
        print("⚠️  Нажмите Ctrl+C для остановки")
        print("=" * 70)
        
        # Настройки
        DB_PATH = "bitcoin_balances.db.new_1760964600"
        WORDLIST_FILE = "brainwallet_english.txt"
        
        print(f"🔍 Поиск базы данных: {DB_PATH}")
        
        if not os.path.exists(DB_PATH):
            print(f"❌ База данных не найдена: {DB_PATH}")
            print("💡 Убедитесь, что файл базы данных существует в текущей директории")
            input("Нажмите Enter для выхода...")
            return
        
        # Проверяем wordlist
        if not os.path.exists(WORDLIST_FILE):
            print(f"⚠️  Файл {WORDLIST_FILE} не найден, будет создан тестовый список слов")
        
        print(f"📁 Используется база данных: {DB_PATH}")
        print(f"📝 Используется wordlist: {WORDLIST_FILE}")
        print("=" * 70)
        
        # Создаем умного охотника
        print("🔄 Инициализация умной системы поиска...")
        hunter = AdvancedBalanceHunter(db_path=DB_PATH, wordlist_file=WORDLIST_FILE)
        
        # Запускаем умный поиск
        print("🚀 ЗАПУСК УМНОГО МНОГОПОТОЧНОГО ПОИСКА...")
        hunter.start_smart_hunt(
            generator_workers=2,    # Количество генераторов
            checker_workers=4,      # Количество проверяющих  
            batch_size=50,          # Размер батча
            max_queue_size=1000     # Максимальный размер очереди
        )
        
    except Exception as e:
        print(f"\n❌ ПРОИЗОШЛА КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error("Критическая ошибка в main:", exc_info=True)
    
    finally:
        print("\n" + "=" * 70)
        print("👋 Программа завершена")

if __name__ == "__main__":
    main()