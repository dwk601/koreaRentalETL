-- Korean Rental ETL - Schema Migration 003
-- Adds illinoisksa.org/housing as the 6th rental listing source

INSERT INTO public.sources (name, display_name, base_url, fetcher_type, schedule_cron, is_active)
VALUES
    ('illinoisksa', 'KSA Illinois', 'https://illinoisksa.org/housing/', 'Fetcher', '0 */6 * * *', TRUE)
ON CONFLICT (name) DO NOTHING;
