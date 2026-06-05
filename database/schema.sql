--
-- PostgreSQL database dump
--

\restrict qVZk2IL9PNmdVsOz3BJc9oYk1rndyVy13z5OUk57ZnGzycDOdl6TuoyWdj7WqRh

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: geopolitical_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geopolitical_events (
    event_id integer NOT NULL,
    date date NOT NULL,
    region text,
    event_type text,
    description text,
    gdelt_score double precision,
    source text DEFAULT 'GDELT'::text
);


--
-- Name: geopolitical_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.geopolitical_events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: geopolitical_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.geopolitical_events_event_id_seq OWNED BY public.geopolitical_events.event_id;


--
-- Name: inventory_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_levels (
    inventory_id integer NOT NULL,
    resource_id integer,
    date date NOT NULL,
    level double precision,
    unit text,
    region text,
    country text DEFAULT 'WORLD'::text,
    wow_change double precision
);


--
-- Name: inventory_levels_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_levels_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_levels_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventory_levels_inventory_id_seq OWNED BY public.inventory_levels.inventory_id;


--
-- Name: news_headlines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.news_headlines (
    headline_id integer NOT NULL,
    resource_id integer,
    date date,
    headline text,
    source text,
    sentiment double precision,
    published_at timestamp without time zone,
    url text
);


--
-- Name: news_headlines_headline_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.news_headlines_headline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: news_headlines_headline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.news_headlines_headline_id_seq OWNED BY public.news_headlines.headline_id;


--
-- Name: prices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prices (
    price_id integer NOT NULL,
    resource_id integer,
    date date NOT NULL,
    value double precision,
    pct_change_1d double precision,
    rolling_avg_7d double precision,
    rolling_avg_30d double precision,
    z_score double precision,
    fetched_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    rolling_std_365d double precision
);


--
-- Name: prices_price_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.prices_price_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: prices_price_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.prices_price_id_seq OWNED BY public.prices.price_id;


--
-- Name: production; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production (
    production_id integer NOT NULL,
    resource_id integer,
    date date NOT NULL,
    region text,
    volume_tbpd double precision,
    type text,
    country text,
    yoy_pct_change double precision,
    gap_tbpd double precision,
    opec_share_pct double precision
);


--
-- Name: production_production_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.production_production_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: production_production_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.production_production_id_seq OWNED BY public.production.production_id;


--
-- Name: resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resources (
    resource_id integer NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    unit text,
    source text,
    frequency text,
    description text
);


--
-- Name: resources_resource_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.resources_resource_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: resources_resource_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.resources_resource_id_seq OWNED BY public.resources.resource_id;


--
-- Name: shortage_signals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shortage_signals (
    signal_id integer NOT NULL,
    resource_id integer,
    date date NOT NULL,
    z_score double precision,
    shortage_score double precision,
    flag text,
    price_dev_pct double precision,
    CONSTRAINT shortage_signals_flag_check CHECK ((flag = ANY (ARRAY['NORMAL'::text, 'RISKY'::text, 'CRITICAL'::text])))
);


--
-- Name: shortage_signals_signal_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shortage_signals_signal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shortage_signals_signal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shortage_signals_signal_id_seq OWNED BY public.shortage_signals.signal_id;


--
-- Name: geopolitical_events event_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geopolitical_events ALTER COLUMN event_id SET DEFAULT nextval('public.geopolitical_events_event_id_seq'::regclass);


--
-- Name: inventory_levels inventory_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_levels ALTER COLUMN inventory_id SET DEFAULT nextval('public.inventory_levels_inventory_id_seq'::regclass);


--
-- Name: news_headlines headline_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news_headlines ALTER COLUMN headline_id SET DEFAULT nextval('public.news_headlines_headline_id_seq'::regclass);


--
-- Name: prices price_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices ALTER COLUMN price_id SET DEFAULT nextval('public.prices_price_id_seq'::regclass);


--
-- Name: production production_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production ALTER COLUMN production_id SET DEFAULT nextval('public.production_production_id_seq'::regclass);


--
-- Name: resources resource_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resources ALTER COLUMN resource_id SET DEFAULT nextval('public.resources_resource_id_seq'::regclass);


--
-- Name: shortage_signals signal_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shortage_signals ALTER COLUMN signal_id SET DEFAULT nextval('public.shortage_signals_signal_id_seq'::regclass);


--
-- Name: geopolitical_events geopolitical_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geopolitical_events
    ADD CONSTRAINT geopolitical_events_pkey PRIMARY KEY (event_id);


--
-- Name: inventory_levels inventory_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_levels
    ADD CONSTRAINT inventory_levels_pkey PRIMARY KEY (inventory_id);


--
-- Name: news_headlines news_headlines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news_headlines
    ADD CONSTRAINT news_headlines_pkey PRIMARY KEY (headline_id);


--
-- Name: prices prices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices
    ADD CONSTRAINT prices_pkey PRIMARY KEY (price_id);


--
-- Name: prices prices_resource_id_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices
    ADD CONSTRAINT prices_resource_id_date_key UNIQUE (resource_id, date);


--
-- Name: production production_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production
    ADD CONSTRAINT production_pkey PRIMARY KEY (production_id);


--
-- Name: resources resources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resources
    ADD CONSTRAINT resources_pkey PRIMARY KEY (resource_id);


--
-- Name: shortage_signals shortage_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shortage_signals
    ADD CONSTRAINT shortage_signals_pkey PRIMARY KEY (signal_id);


--
-- Name: shortage_signals shortage_signals_resource_id_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shortage_signals
    ADD CONSTRAINT shortage_signals_resource_id_date_key UNIQUE (resource_id, date);


--
-- Name: inventory_levels inventory_levels_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_levels
    ADD CONSTRAINT inventory_levels_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id);


--
-- Name: news_headlines news_headlines_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.news_headlines
    ADD CONSTRAINT news_headlines_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id);


--
-- Name: prices prices_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prices
    ADD CONSTRAINT prices_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id);


--
-- Name: production production_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production
    ADD CONSTRAINT production_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id);


--
-- Name: shortage_signals shortage_signals_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shortage_signals
    ADD CONSTRAINT shortage_signals_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id);


--
-- PostgreSQL database dump complete
--

\unrestrict qVZk2IL9PNmdVsOz3BJc9oYk1rndyVy13z5OUk57ZnGzycDOdl6TuoyWdj7WqRh

