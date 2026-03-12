--
-- PostgreSQL database dump
--

\restrict r3XR4XqTBtdFCjfASklT1sl8rAmauYz0g9BE9uewaaq2jjGU6xT2NPUIMUHlQ7Z

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: campaign; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.campaign (
    campaign_id uuid NOT NULL,
    publisher_id uuid NOT NULL,
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone
);


--
-- Name: derived_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.derived_metrics (
    bucket_timestamp timestamp with time zone NOT NULL,
    publisher_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    impressions_mean double precision,
    clicks_mean double precision,
    conversions_mean double precision,
    impressions_std double precision,
    clicks_std double precision,
    conversions_std double precision,
    impressions_weighted_mean double precision,
    clicks_weighted_mean double precision,
    conversions_weighted_mean double precision,
    sample_size integer DEFAULT 250 NOT NULL
);


--
-- Name: ml_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ml_reports (
    model_run_id uuid NOT NULL,
    publisher_id uuid NOT NULL,
    report_timestamp timestamp with time zone NOT NULL,
    report_data jsonb
);


--
-- Name: model_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_logs (
    "timestamp" timestamp with time zone NOT NULL,
    model_name text NOT NULL,
    score numeric(3,2) NOT NULL,
    publisher_id uuid NOT NULL,
    CONSTRAINT model_logs_score_check CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric)))
);


--
-- Name: model_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_runs (
    model_run_id uuid NOT NULL,
    model_name text NOT NULL
);


--
-- Name: publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publishers (
    publisher_name text NOT NULL,
    publisher_id uuid NOT NULL
);


--
-- Name: raw_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_metrics (
    bucket_timestamp timestamp with time zone NOT NULL,
    impression_count integer DEFAULT 0 NOT NULL,
    click_count integer DEFAULT 0 NOT NULL,
    conversion_count integer DEFAULT 0 NOT NULL,
    publisher_id uuid NOT NULL,
    campaign_id uuid NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: campaign campaign_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign
    ADD CONSTRAINT campaign_pkey PRIMARY KEY (campaign_id);


--
-- Name: derived_metrics derived_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.derived_metrics
    ADD CONSTRAINT derived_metrics_pkey PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id);


--
-- Name: ml_reports ml_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ml_reports
    ADD CONSTRAINT ml_reports_pkey PRIMARY KEY (model_run_id, publisher_id, report_timestamp);


--
-- Name: model_logs model_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_logs
    ADD CONSTRAINT model_logs_pkey PRIMARY KEY (publisher_id, "timestamp");


--
-- Name: model_runs model_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_runs
    ADD CONSTRAINT model_runs_pkey PRIMARY KEY (model_run_id);


--
-- Name: publishers publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publishers
    ADD CONSTRAINT publishers_pkey PRIMARY KEY (publisher_id);


--
-- Name: raw_metrics raw_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_metrics
    ADD CONSTRAINT raw_metrics_pkey PRIMARY KEY (publisher_id, bucket_timestamp, campaign_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: derived_metrics_bucket_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX derived_metrics_bucket_timestamp_idx ON public.derived_metrics USING btree (bucket_timestamp DESC);


--
-- Name: model_logs_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX model_logs_timestamp_idx ON public.model_logs USING btree ("timestamp" DESC);


--
-- Name: raw_metrics_bucket_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_metrics_bucket_timestamp_idx ON public.raw_metrics USING btree (bucket_timestamp DESC);


--
-- Name: campaign campaign_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.campaign
    ADD CONSTRAINT campaign_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- Name: derived_metrics derived_metrics_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.derived_metrics
    ADD CONSTRAINT derived_metrics_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaign(campaign_id) ON DELETE CASCADE;


--
-- Name: derived_metrics derived_metrics_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.derived_metrics
    ADD CONSTRAINT derived_metrics_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- Name: ml_reports ml_reports_model_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ml_reports
    ADD CONSTRAINT ml_reports_model_run_id_fkey FOREIGN KEY (model_run_id) REFERENCES public.model_runs(model_run_id) ON DELETE CASCADE;


--
-- Name: ml_reports ml_reports_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ml_reports
    ADD CONSTRAINT ml_reports_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- Name: model_logs model_logs_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_logs
    ADD CONSTRAINT model_logs_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- Name: raw_metrics raw_metrics_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_metrics
    ADD CONSTRAINT raw_metrics_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.campaign(campaign_id) ON DELETE CASCADE;


--
-- Name: raw_metrics raw_metrics_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_metrics
    ADD CONSTRAINT raw_metrics_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict r3XR4XqTBtdFCjfASklT1sl8rAmauYz0g9BE9uewaaq2jjGU6xT2NPUIMUHlQ7Z

