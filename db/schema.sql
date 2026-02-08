--
-- PostgreSQL database dump
--

\restrict WLqhFzidAfP4wGoAM0pihGOhltRdwGDDCKyF6WWXjaXiv6usfXM3mfJlQ8TbRdk

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
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: impression; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.impression (
    impression_ts timestamp with time zone NOT NULL,
    impression_date date NOT NULL,
    impression_time time without time zone NOT NULL,
    impression_clicks integer NOT NULL
);


ALTER TABLE public.impression OWNER TO postgres;

--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: impression_impression_ts_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX impression_impression_ts_idx ON public.impression USING btree (impression_ts DESC);


--
-- PostgreSQL database dump complete
--

\unrestrict WLqhFzidAfP4wGoAM0pihGOhltRdwGDDCKyF6WWXjaXiv6usfXM3mfJlQ8TbRdk

