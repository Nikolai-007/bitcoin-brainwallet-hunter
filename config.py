DATABASE_CONFIG = {
    'path': 'bitcoin_balances.db',
    'table_name': 'balances'
}

PHRASE_GENERATION = {
    'wordlist_file': 'brainwallet_english.txt'
}

THREADING_CONFIG = {
    'generator_workers': 2,
    'checker_workers': 4,
    'batch_size': 50
}

EDUCATIONAL_MODE = True