-- Сохраните этот код в файл create_database.sql
CREATE TABLE IF NOT EXISTS bitcoin_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT UNIQUE NOT NULL,
    balance REAL NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO bitcoin_balances (address, balance) VALUES
('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', 1000000.0),
('34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo', 250000.5),
('3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r', 180000.75),
('3JJmF63ifcamPLiAmLgG96RA599yNtY3EQ', 120000.25),
('bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6', 95000.8),
('bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', 87000.3),
('3Kzh9qAqVWQhEsfQz7zEQL1EuSJ5ALJQYJ', 75000.6),
('38UmuUqPCrFmQo4khkomQwZ4VbY2nZMJ67', 68000.9),
('3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW8c', 52000.4),
('3FkenCiXpSLqD8L79intRNXUgjRoH9sjXa', 45000.1);

SELECT "База данных успешно создана!" as status;
SELECT address, balance FROM bitcoin_balances ORDER BY balance DESC;