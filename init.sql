-- Initialize tables for strictly relational data (Billing, User Auth)

CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL, -- Credit amount
    status VARCHAR(50) NOT NULL,    -- 'COMPLETED', 'PENDING', 'FAILED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_jobs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,    -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed some initial data
INSERT INTO tenants (name) VALUES 
('Acme Corp'), 
('Globex Corporation'),
('Wayne Enterprises'),
('Stark Industries')
ON CONFLICT DO NOTHING;

INSERT INTO users (tenant_id, email, hashed_password) VALUES 
(1, 'admin@acmecorp.com', 'hashed123'),
(2, 'admin@globex.com', 'hashed456'),
(3, 'admin@wayne.com', 'hashed789'),
(4, 'admin@stark.com', 'hashed000') 
ON CONFLICT DO NOTHING;
