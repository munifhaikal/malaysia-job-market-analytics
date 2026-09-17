-- ============================================================
-- MALAYSIA JOB MARKET ANALYTICS
-- Medallion Architecture using PostgreSQL Schemas
-- raw → staging → analytics
-- ============================================================


-- ------------------------------------------------------------
-- CREATE SCHEMAS
-- ------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;


-- ------------------------------------------------------------
-- RAW SCHEMA
-- Stores API response exactly as received
-- Never modified after insertion
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.jobs (
    id SERIAL PRIMARY KEY,
    raw_json JSONB NOT NULL,
    data_source VARCHAR(20) NOT NULL,
    search_query VARCHAR(100),
    ingested_at TIMESTAMP DEFAULT NOW()
);


-- ------------------------------------------------------------
-- STAGING SCHEMA
-- Cleaned, standardised, deduplicated
-- Consistent columns regardless of source API
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    job_title VARCHAR(255),
    employer_name VARCHAR(255),
    job_location VARCHAR(255),
    job_city VARCHAR(255),
    job_country VARCHAR(10),
    job_employment_type VARCHAR(50),
    job_is_remote BOOLEAN,
    job_description TEXT,
    job_min_salary NUMERIC,
    job_max_salary NUMERIC,
    job_salary_period VARCHAR(20),
    job_posted_at_datetime_utc TIMESTAMP,
    job_apply_link TEXT,
    job_publisher VARCHAR(255),
    search_query VARCHAR(100),
    data_source VARCHAR(20),
    cleaned_at TIMESTAMP DEFAULT NOW()
);


-- ------------------------------------------------------------
-- ANALYTICS SCHEMA
-- Enriched with derived fields
-- Business-ready for analytics, ML, and dashboard
-- All downstream tables reference this schema
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.jobs (
    job_id VARCHAR(255) PRIMARY KEY REFERENCES staging.jobs(job_id),
    job_title VARCHAR(255),
    employer_name VARCHAR(255),
    job_location VARCHAR(255),
    job_city VARCHAR(255),
    job_country VARCHAR(10),
    job_employment_type VARCHAR(50),
    job_is_remote BOOLEAN,
    job_description TEXT,
    job_min_salary NUMERIC,
    job_max_salary NUMERIC,
    job_salary_period VARCHAR(20),
    job_posted_at_datetime_utc TIMESTAMP,
    job_apply_link TEXT,
    job_publisher VARCHAR(255),
    search_query VARCHAR(100),
    data_source VARCHAR(20),
    seniority_level VARCHAR(50),
    work_arrangement VARCHAR(20),
    job_function VARCHAR(50),
    enriched_at TIMESTAMP DEFAULT NOW()
);


-- ------------------------------------------------------------
-- ENRICHMENT TABLES
-- All reference analytics.jobs via job_id
-- Populated by LLM extraction
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.extracted_skills (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES analytics.jobs(job_id),
    skill_name VARCHAR(255),
    skill_category VARCHAR(100),
    requirement_type VARCHAR(20),
    proficiency_level VARCHAR(20),
    extraction_source VARCHAR(20),
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.job_education_requirements (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES analytics.jobs(job_id),
    degree_level VARCHAR(50),
    degree_field TEXT,
    requirement_type VARCHAR(20),
    extraction_source VARCHAR(20),
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.job_experience_requirements (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES analytics.jobs(job_id),
    min_years INTEGER,
    max_years INTEGER,
    requirement_type VARCHAR(20),
    extraction_source VARCHAR(20),
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.job_certifications (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES analytics.jobs(job_id),
    certification_name VARCHAR(255),
    requirement_type VARCHAR(20),
    extraction_source VARCHAR(20),
    extracted_at TIMESTAMP DEFAULT NOW()
);


-- ------------------------------------------------------------
-- PIPELINE LOGS
-- Tracks each ETL run with counts per layer
-- Sits outside schemas, standalone operational table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pipeline_logs (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT NOW(),
    search_query VARCHAR(100),
    data_source VARCHAR(20),
    raw_inserted INTEGER DEFAULT 0,
    staging_inserted INTEGER DEFAULT 0,
    staging_skipped INTEGER DEFAULT 0,
    analytics_inserted INTEGER DEFAULT 0,
    status VARCHAR(20),
    error_message TEXT
);