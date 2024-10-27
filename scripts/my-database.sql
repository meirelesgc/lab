CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TYPE pipeline_status AS ENUM ('STANDBY', 'IN-PROCESS', 'FAILED', 'DONE');
CREATE TABLE IF NOT EXISTS parameters (
    parameter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parameter VARCHAR(255) NOT NULL,
    synonyms TEXT[] DEFAULT '{}' 
);
CREATE TABLE IF NOT EXISTS patients (
    patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE,
    identifier VARCHAR 
);
CREATE TABLE IF NOT EXISTS documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    document TEXT,
    status pipeline_status DEFAULT 'IN-PROCESS',
    patient_id UUID REFERENCES patients(patient_id) ON DELETE CASCADE,
    unverified_patient UUID[] DEFAULT '{}' CHECK (array_length(unverified_patient, 1) <= 5),
    document_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
