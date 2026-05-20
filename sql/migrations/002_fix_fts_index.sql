-- Korean Rental ETL - Schema Migration 002
-- Fix FTS index to handle NULL fields using COALESCE

-- Drop the old index that excludes NULL values
DROP INDEX IF EXISTS idx_listings_korean_fts;

-- Create the fixed index that includes NULL fields via COALESCE
CREATE INDEX idx_listings_korean_fts ON public.listings USING GIN ((COALESCE(title_ko,'') || ' ' || COALESCE(body_ko,'') || ' ' || COALESCE(address_raw,'')) gin_trgm_ops);
