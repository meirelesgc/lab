CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE pipeline_status AS ENUM ('STANDBY', 'IN-PROCESS', 'FAILED');

CREATE TABLE IF NOT EXISTS documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    document TEXT,
    status pipeline_status DEFAULT 'IN-PROCESS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS parameters (
    parameter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parameter VARCHAR(255) NOT NULL,
    synonyms TEXT[]
);