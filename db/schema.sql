--
-- PostgreSQL database dump
--

\restrict EcdpDJhBGSrS1rWEakbwqLCx2TyiLDDxoCo4RWeHDXvfY7NbxqkAJBl5VqNyRBG

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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: model_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_logs (
    "timestamp" timestamp with time zone NOT NULL,
    publisher_id integer NOT NULL,
    model_name text NOT NULL,
    score numeric(3,2) NOT NULL,
    CONSTRAINT model_logs_score_check CHECK (((score >= (0)::numeric) AND (score <= (1)::numeric)))
);


--
-- Name: publishers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.publishers (
    publisher_id integer NOT NULL,
    publisher_name text NOT NULL
);


--
-- Name: raw_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_metrics (
    bucket_timestamp timestamp with time zone NOT NULL,
    publisher_id integer NOT NULL,
    impression_count integer DEFAULT 0 NOT NULL,
    click_count integer DEFAULT 0 NOT NULL,
    conversion_count integer DEFAULT 0 NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: model_logs model_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_logs
    ADD CONSTRAINT model_logs_pkey PRIMARY KEY (publisher_id, "timestamp");


--
-- Name: publishers publishers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.publishers
    ADD CONSTRAINT publishers_pkey PRIMARY KEY (publisher_id);


--
-- Name: raw_metrics raw_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_metrics
    ADD CONSTRAINT raw_metrics_pkey PRIMARY KEY (publisher_id, bucket_timestamp);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: raw_metrics_bucket_timestamp_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_metrics_bucket_timestamp_idx ON public.raw_metrics USING btree (bucket_timestamp DESC);


--
-- Name: model_logs model_logs_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_logs
    ADD CONSTRAINT model_logs_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- Name: raw_metrics raw_metrics_publisher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_metrics
    ADD CONSTRAINT raw_metrics_publisher_id_fkey FOREIGN KEY (publisher_id) REFERENCES public.publishers(publisher_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict EcdpDJhBGSrS1rWEakbwqLCx2TyiLDDxoCo4RWeHDXvfY7NbxqkAJBl5VqNyRBG

