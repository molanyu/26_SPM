--
-- PostgreSQL database dump
--

\restrict kgYPBNmhHwoRmfN71mQnWoxi5h8BPFkcic9fRCjmB9OYkuIbRs4hGIujI7hCZOy

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg13+1)

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

ALTER TABLE IF EXISTS ONLY public.violation_records DROP CONSTRAINT IF EXISTS violation_records_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.violation_records DROP CONSTRAINT IF EXISTS violation_records_reservation_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_department_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.study_rooms DROP CONSTRAINT IF EXISTS study_rooms_department_id_fkey;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS seats_room_id_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_role_id_fkey;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_permission_id_fkey;
ALTER TABLE IF EXISTS ONLY public.reservations DROP CONSTRAINT IF EXISTS reservations_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.reservations DROP CONSTRAINT IF EXISTS reservations_seat_id_fkey;
ALTER TABLE IF EXISTS ONLY public.reservations DROP CONSTRAINT IF EXISTS reservations_room_id_fkey;
ALTER TABLE IF EXISTS ONLY public.notification_logs DROP CONSTRAINT IF EXISTS notification_logs_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.notification_logs DROP CONSTRAINT IF EXISTS notification_logs_reservation_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS checkin_records_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS checkin_records_seat_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS checkin_records_room_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS checkin_records_reservation_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checkin_codes DROP CONSTRAINT IF EXISTS checkin_codes_room_id_fkey;
DROP INDEX IF EXISTS public.ix_violation_records_violation_type;
DROP INDEX IF EXISTS public.ix_violation_records_user_id;
DROP INDEX IF EXISTS public.ix_violation_records_reservation_id;
DROP INDEX IF EXISTS public.ix_violation_records_occurred_at;
DROP INDEX IF EXISTS public.ix_users_student_no;
DROP INDEX IF EXISTS public.ix_users_email;
DROP INDEX IF EXISTS public.ix_users_department_id;
DROP INDEX IF EXISTS public.ix_system_configs_config_key;
DROP INDEX IF EXISTS public.ix_study_rooms_department_id;
DROP INDEX IF EXISTS public.ix_seats_room_id;
DROP INDEX IF EXISTS public.ix_roles_code;
DROP INDEX IF EXISTS public.ix_reservations_user_status_time;
DROP INDEX IF EXISTS public.ix_reservations_user_id;
DROP INDEX IF EXISTS public.ix_reservations_status;
DROP INDEX IF EXISTS public.ix_reservations_start_time;
DROP INDEX IF EXISTS public.ix_reservations_seat_status_time;
DROP INDEX IF EXISTS public.ix_reservations_seat_id;
DROP INDEX IF EXISTS public.ix_reservations_room_id;
DROP INDEX IF EXISTS public.ix_reservations_end_time;
DROP INDEX IF EXISTS public.ix_permissions_code;
DROP INDEX IF EXISTS public.ix_notification_logs_user_id;
DROP INDEX IF EXISTS public.ix_notification_logs_status;
DROP INDEX IF EXISTS public.ix_notification_logs_sent_at;
DROP INDEX IF EXISTS public.ix_notification_logs_reservation_id;
DROP INDEX IF EXISTS public.ix_notification_logs_notification_type;
DROP INDEX IF EXISTS public.ix_departments_code;
DROP INDEX IF EXISTS public.ix_checkin_records_user_id;
DROP INDEX IF EXISTS public.ix_checkin_records_seat_id;
DROP INDEX IF EXISTS public.ix_checkin_records_room_id;
DROP INDEX IF EXISTS public.ix_checkin_records_reservation_id;
DROP INDEX IF EXISTS public.ix_checkin_records_checkin_at;
DROP INDEX IF EXISTS public.ix_checkin_codes_room_id;
DROP INDEX IF EXISTS public.ix_checkin_codes_code_date;
ALTER TABLE IF EXISTS ONLY public.violation_records DROP CONSTRAINT IF EXISTS violation_records_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_student_no_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS user_roles_pkey;
ALTER TABLE IF EXISTS ONLY public.violation_records DROP CONSTRAINT IF EXISTS uq_violation_records_reservation_type;
ALTER TABLE IF EXISTS ONLY public.user_roles DROP CONSTRAINT IF EXISTS uq_user_roles_user_role;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS uq_seats_room_code;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS uq_role_permissions_role_permission;
ALTER TABLE IF EXISTS ONLY public.notification_logs DROP CONSTRAINT IF EXISTS uq_notification_logs_reservation_type;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS uq_checkin_records_reservation;
ALTER TABLE IF EXISTS ONLY public.checkin_codes DROP CONSTRAINT IF EXISTS uq_checkin_codes_room_date;
ALTER TABLE IF EXISTS ONLY public.system_configs DROP CONSTRAINT IF EXISTS system_configs_pkey;
ALTER TABLE IF EXISTS ONLY public.system_configs DROP CONSTRAINT IF EXISTS system_configs_config_key_key;
ALTER TABLE IF EXISTS ONLY public.study_rooms DROP CONSTRAINT IF EXISTS study_rooms_pkey;
ALTER TABLE IF EXISTS ONLY public.seats DROP CONSTRAINT IF EXISTS seats_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_pkey;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_name_key;
ALTER TABLE IF EXISTS ONLY public.roles DROP CONSTRAINT IF EXISTS roles_code_key;
ALTER TABLE IF EXISTS ONLY public.role_permissions DROP CONSTRAINT IF EXISTS role_permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.reservations DROP CONSTRAINT IF EXISTS reservations_pkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_pkey;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_name_key;
ALTER TABLE IF EXISTS ONLY public.permissions DROP CONSTRAINT IF EXISTS permissions_code_key;
ALTER TABLE IF EXISTS ONLY public.notification_logs DROP CONSTRAINT IF EXISTS notification_logs_pkey;
ALTER TABLE IF EXISTS ONLY public.departments DROP CONSTRAINT IF EXISTS departments_pkey;
ALTER TABLE IF EXISTS ONLY public.departments DROP CONSTRAINT IF EXISTS departments_name_key;
ALTER TABLE IF EXISTS ONLY public.departments DROP CONSTRAINT IF EXISTS departments_code_key;
ALTER TABLE IF EXISTS ONLY public.checkin_records DROP CONSTRAINT IF EXISTS checkin_records_pkey;
ALTER TABLE IF EXISTS ONLY public.checkin_codes DROP CONSTRAINT IF EXISTS checkin_codes_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.violation_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.user_roles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.system_configs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.study_rooms ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.seats ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.roles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.role_permissions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.reservations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.permissions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.notification_logs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.departments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checkin_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checkin_codes ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.violation_records_id_seq;
DROP TABLE IF EXISTS public.violation_records;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.user_roles_id_seq;
DROP TABLE IF EXISTS public.user_roles;
DROP SEQUENCE IF EXISTS public.system_configs_id_seq;
DROP TABLE IF EXISTS public.system_configs;
DROP SEQUENCE IF EXISTS public.study_rooms_id_seq;
DROP TABLE IF EXISTS public.study_rooms;
DROP SEQUENCE IF EXISTS public.seats_id_seq;
DROP TABLE IF EXISTS public.seats;
DROP SEQUENCE IF EXISTS public.roles_id_seq;
DROP TABLE IF EXISTS public.roles;
DROP SEQUENCE IF EXISTS public.role_permissions_id_seq;
DROP TABLE IF EXISTS public.role_permissions;
DROP SEQUENCE IF EXISTS public.reservations_id_seq;
DROP TABLE IF EXISTS public.reservations;
DROP SEQUENCE IF EXISTS public.permissions_id_seq;
DROP TABLE IF EXISTS public.permissions;
DROP SEQUENCE IF EXISTS public.notification_logs_id_seq;
DROP TABLE IF EXISTS public.notification_logs;
DROP SEQUENCE IF EXISTS public.departments_id_seq;
DROP TABLE IF EXISTS public.departments;
DROP SEQUENCE IF EXISTS public.checkin_records_id_seq;
DROP TABLE IF EXISTS public.checkin_records;
DROP SEQUENCE IF EXISTS public.checkin_codes_id_seq;
DROP TABLE IF EXISTS public.checkin_codes;
DROP TABLE IF EXISTS public.alembic_version;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO spm;

--
-- Name: checkin_codes; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.checkin_codes (
    id integer NOT NULL,
    room_id integer NOT NULL,
    code character varying(20) NOT NULL,
    code_date date NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.checkin_codes OWNER TO spm;

--
-- Name: checkin_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.checkin_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.checkin_codes_id_seq OWNER TO spm;

--
-- Name: checkin_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.checkin_codes_id_seq OWNED BY public.checkin_codes.id;


--
-- Name: checkin_records; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.checkin_records (
    id integer NOT NULL,
    reservation_id integer NOT NULL,
    user_id integer NOT NULL,
    room_id integer NOT NULL,
    seat_id integer NOT NULL,
    checkin_method character varying(20) NOT NULL,
    checkin_at timestamp without time zone NOT NULL,
    is_valid boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_checkin_records_method CHECK (((checkin_method)::text = ANY ((ARRAY['CODE'::character varying, 'QRCODE'::character varying])::text[])))
);


ALTER TABLE public.checkin_records OWNER TO spm;

--
-- Name: checkin_records_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.checkin_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.checkin_records_id_seq OWNER TO spm;

--
-- Name: checkin_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.checkin_records_id_seq OWNED BY public.checkin_records.id;


--
-- Name: departments; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.departments (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(50) NOT NULL,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.departments OWNER TO spm;

--
-- Name: departments_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.departments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.departments_id_seq OWNER TO spm;

--
-- Name: departments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.departments_id_seq OWNED BY public.departments.id;


--
-- Name: notification_logs; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.notification_logs (
    id integer NOT NULL,
    user_id integer NOT NULL,
    reservation_id integer NOT NULL,
    notification_type character varying(50) NOT NULL,
    channel character varying(20) DEFAULT 'MOCK'::character varying NOT NULL,
    status character varying(20) NOT NULL,
    message text NOT NULL,
    sent_at timestamp without time zone NOT NULL,
    CONSTRAINT ck_notification_logs_channel CHECK (((channel)::text = ANY ((ARRAY['MOCK'::character varying, 'SMTP_EMAIL'::character varying])::text[]))),
    CONSTRAINT ck_notification_logs_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'SENT'::character varying, 'FAILED'::character varying])::text[]))),
    CONSTRAINT ck_notification_logs_type CHECK (((notification_type)::text = ANY ((ARRAY['RESERVATION_REMINDER'::character varying, 'NO_SHOW_REMINDER'::character varying, 'AUTO_CANCEL_NOTICE'::character varying])::text[])))
);


ALTER TABLE public.notification_logs OWNER TO spm;

--
-- Name: notification_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.notification_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notification_logs_id_seq OWNER TO spm;

--
-- Name: notification_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.notification_logs_id_seq OWNED BY public.notification_logs.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(100) NOT NULL,
    description text
);


ALTER TABLE public.permissions OWNER TO spm;

--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.permissions_id_seq OWNER TO spm;

--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: reservations; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.reservations (
    id integer NOT NULL,
    user_id integer NOT NULL,
    seat_id integer NOT NULL,
    room_id integer NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    status character varying(20) NOT NULL,
    created_by character varying(20) NOT NULL,
    cancelled_by character varying(20),
    cancel_reason text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_reservations_cancelled_by CHECK (((cancelled_by IS NULL) OR ((cancelled_by)::text = ANY ((ARRAY['STUDENT'::character varying, 'ADMIN'::character varying])::text[])))),
    CONSTRAINT ck_reservations_created_by CHECK (((created_by)::text = ANY ((ARRAY['STUDENT'::character varying, 'ADMIN'::character varying])::text[]))),
    CONSTRAINT ck_reservations_status CHECK (((status)::text = ANY ((ARRAY['BOOKED'::character varying, 'CANCELLED'::character varying, 'CHECKED_IN'::character varying, 'EXPIRED'::character varying])::text[]))),
    CONSTRAINT ck_reservations_time_range CHECK ((start_time < end_time))
);


ALTER TABLE public.reservations OWNER TO spm;

--
-- Name: reservations_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.reservations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reservations_id_seq OWNER TO spm;

--
-- Name: reservations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.reservations_id_seq OWNED BY public.reservations.id;


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.role_permissions (
    id integer NOT NULL,
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.role_permissions OWNER TO spm;

--
-- Name: role_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.role_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.role_permissions_id_seq OWNER TO spm;

--
-- Name: role_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.role_permissions_id_seq OWNED BY public.role_permissions.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.roles OWNER TO spm;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO spm;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: seats; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.seats (
    id integer NOT NULL,
    room_id integer NOT NULL,
    seat_code character varying(50) NOT NULL,
    seat_label character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_window_side boolean DEFAULT false NOT NULL,
    has_power_socket boolean DEFAULT false NOT NULL,
    has_track_socket boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.seats OWNER TO spm;

--
-- Name: seats_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.seats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.seats_id_seq OWNER TO spm;

--
-- Name: seats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.seats_id_seq OWNED BY public.seats.id;


--
-- Name: study_rooms; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.study_rooms (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    location character varying(255) NOT NULL,
    department_id integer,
    is_department_only boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    open_time time without time zone NOT NULL,
    close_time time without time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.study_rooms OWNER TO spm;

--
-- Name: study_rooms_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.study_rooms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.study_rooms_id_seq OWNER TO spm;

--
-- Name: study_rooms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.study_rooms_id_seq OWNED BY public.study_rooms.id;


--
-- Name: system_configs; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.system_configs (
    id integer NOT NULL,
    config_key character varying(100) NOT NULL,
    config_value text NOT NULL,
    value_type character varying(50) NOT NULL,
    description text,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.system_configs OWNER TO spm;

--
-- Name: system_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.system_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_configs_id_seq OWNER TO spm;

--
-- Name: system_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.system_configs_id_seq OWNED BY public.system_configs.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.user_roles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    role_id integer NOT NULL
);


ALTER TABLE public.user_roles OWNER TO spm;

--
-- Name: user_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.user_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_roles_id_seq OWNER TO spm;

--
-- Name: user_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.user_roles_id_seq OWNED BY public.user_roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.users (
    id integer NOT NULL,
    student_no character varying(50),
    name character varying(100) NOT NULL,
    email character varying(255),
    password_hash text NOT NULL,
    department_id integer,
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp without time zone,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_users_login_identifier_present CHECK ((((student_no IS NOT NULL) AND (length(TRIM(BOTH FROM student_no)) > 0)) OR ((email IS NOT NULL) AND (length(TRIM(BOTH FROM email)) > 0)))),
    CONSTRAINT ck_users_password_hash_present CHECK (((password_hash IS NOT NULL) AND (length(TRIM(BOTH FROM password_hash)) > 0)))
);


ALTER TABLE public.users OWNER TO spm;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO spm;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: violation_records; Type: TABLE; Schema: public; Owner: spm
--

CREATE TABLE public.violation_records (
    id integer NOT NULL,
    user_id integer NOT NULL,
    reservation_id integer NOT NULL,
    violation_type character varying(50) NOT NULL,
    occurred_at timestamp without time zone NOT NULL,
    remark text,
    created_at timestamp without time zone NOT NULL,
    CONSTRAINT ck_violation_records_type CHECK (((violation_type)::text = 'NO_SHOW_TIMEOUT'::text))
);


ALTER TABLE public.violation_records OWNER TO spm;

--
-- Name: violation_records_id_seq; Type: SEQUENCE; Schema: public; Owner: spm
--

CREATE SEQUENCE public.violation_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.violation_records_id_seq OWNER TO spm;

--
-- Name: violation_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: spm
--

ALTER SEQUENCE public.violation_records_id_seq OWNED BY public.violation_records.id;


--
-- Name: checkin_codes id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_codes ALTER COLUMN id SET DEFAULT nextval('public.checkin_codes_id_seq'::regclass);


--
-- Name: checkin_records id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records ALTER COLUMN id SET DEFAULT nextval('public.checkin_records_id_seq'::regclass);


--
-- Name: departments id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.departments ALTER COLUMN id SET DEFAULT nextval('public.departments_id_seq'::regclass);


--
-- Name: notification_logs id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.notification_logs ALTER COLUMN id SET DEFAULT nextval('public.notification_logs_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: reservations id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.reservations ALTER COLUMN id SET DEFAULT nextval('public.reservations_id_seq'::regclass);


--
-- Name: role_permissions id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.role_permissions ALTER COLUMN id SET DEFAULT nextval('public.role_permissions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: seats id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.seats ALTER COLUMN id SET DEFAULT nextval('public.seats_id_seq'::regclass);


--
-- Name: study_rooms id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.study_rooms ALTER COLUMN id SET DEFAULT nextval('public.study_rooms_id_seq'::regclass);


--
-- Name: system_configs id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.system_configs ALTER COLUMN id SET DEFAULT nextval('public.system_configs_id_seq'::regclass);


--
-- Name: user_roles id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.user_roles ALTER COLUMN id SET DEFAULT nextval('public.user_roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: violation_records id; Type: DEFAULT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.violation_records ALTER COLUMN id SET DEFAULT nextval('public.violation_records_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.alembic_version (version_num) FROM stdin;
20260506_000005
\.


--
-- Data for Name: checkin_codes; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.checkin_codes (id, room_id, code, code_date, expires_at, created_at) FROM stdin;
1	7	861087	2026-04-30	2026-05-01 00:00:00	2026-04-30 10:58:00
\.


--
-- Data for Name: checkin_records; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.checkin_records (id, reservation_id, user_id, room_id, seat_id, checkin_method, checkin_at, is_valid, created_at, updated_at) FROM stdin;
1	6	4	7	3	CODE	2026-05-06 17:05:41.237506	t	2026-05-06 09:05:41.248506+00	2026-05-06 09:05:41.248511+00
\.


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.departments (id, name, code, is_active) FROM stdin;
1	Postgres Department c9b4779b	PGC9B4779B	t
2	MANUAL-20260429-01-学院	MANUAL-20260429-01-DEPT	t
\.


--
-- Data for Name: notification_logs; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.notification_logs (id, user_id, reservation_id, notification_type, channel, status, message, sent_at) FROM stdin;
2	1	1	RESERVATION_REMINDER	SMTP_EMAIL	SENT	QQ SMTP ???????????????	2026-04-23 11:01:29.817371
3	4	4	AUTO_CANCEL_NOTICE	SMTP_EMAIL	SENT	您的自习室预约已因超时未签到被释放，座位已释放。\n预约 ID：4\n自习室：MANUAL-20260429-01-ROOM\n座位：MANUAL-20260429-01-NORMAL\n开始时间：2026-04-29 09:00\n结束时间：2026-04-29 10:00	2026-05-06 17:35:00
4	4	3	AUTO_CANCEL_NOTICE	SMTP_EMAIL	SENT	您的自习室预约已因超时未签到被释放，座位已释放。\n预约 ID：3\n自习室：MANUAL-20260429-01-ROOM\n座位：MANUAL-20260429-01-NORMAL\n开始时间：2026-04-30 09:00\n结束时间：2026-04-30 10:00	2026-05-06 17:35:00
5	4	5	AUTO_CANCEL_NOTICE	SMTP_EMAIL	SENT	您的自习室预约已因超时未签到被释放，座位已释放。\n预约 ID：5\n自习室：MANUAL-20260429-01-ROOM\n座位：MANUAL-20260429-01-NOSHOW\n开始时间：2026-04-30 09:00\n结束时间：2026-04-30 10:00	2026-05-06 17:35:00
6	4	7	AUTO_CANCEL_NOTICE	SMTP_EMAIL	SENT	您的自习室预约已因超时未签到被释放，座位已释放。\n预约 ID：7\n自习室：MANUAL-20260429-01-ROOM\n座位：MANUAL-20260429-01-NOSHOW\n开始时间：2026-05-06 17:00\n结束时间：2026-05-06 19:00	2026-05-06 17:35:00
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.permissions (id, name, code, description) FROM stdin;
1	Admin Portal Access	admin.portal.access	Allows admin portal login.
2	Read Roles	identity.roles.read	Allows reading roles.
3	Write Roles	identity.roles.write	Allows creating and updating roles.
4	Read Permissions	identity.permissions.read	Allows reading permissions.
5	Assign User Roles	identity.users.roles.write	Allows assigning roles to users.
6	创建用户账号	identity.users.write	允许创建单个学生账号或管理员账号。
7	维护院系	identity.departments.write	允许查看、新增、启用和停用院系。
\.


--
-- Data for Name: reservations; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.reservations (id, user_id, seat_id, room_id, start_time, end_time, status, created_by, cancelled_by, cancel_reason, created_at, updated_at) FROM stdin;
1	1	1	1	2026-04-21 15:00:00	2026-04-21 17:00:00	CANCELLED	STUDENT	STUDENT	学生端主动取消	2026-04-20 07:03:31.642312+00	2026-04-20 07:23:09.185964+00
2	1	1	1	2026-04-20 16:00:00	2026-04-20 18:00:00	CANCELLED	STUDENT	STUDENT	学生端主动取消	2026-04-20 07:22:40.028129+00	2026-04-20 07:23:12.16492+00
6	4	3	7	2026-05-06 17:00:00	2026-05-06 19:00:00	CHECKED_IN	STUDENT	\N	\N	2026-05-06 08:44:00.498669+00	2026-05-06 09:05:41.256629+00
4	4	3	7	2026-04-29 09:00:00	2026-04-29 10:00:00	EXPIRED	STUDENT	\N	\N	2026-04-29 09:02:56.70429+00	2026-05-06 09:35:01.741312+00
3	4	3	7	2026-04-30 09:00:00	2026-04-30 10:00:00	EXPIRED	STUDENT	\N	\N	2026-04-29 08:58:26.351459+00	2026-05-06 09:35:01.756354+00
5	4	4	7	2026-04-30 09:00:00	2026-04-30 10:00:00	EXPIRED	STUDENT	\N	\N	2026-04-29 09:03:53.764686+00	2026-05-06 09:35:01.764247+00
7	4	4	7	2026-05-06 17:00:00	2026-05-06 19:00:00	EXPIRED	STUDENT	\N	\N	2026-05-06 08:44:26.004579+00	2026-05-06 09:35:01.771182+00
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.role_permissions (id, role_id, permission_id) FROM stdin;
1	1	1
2	1	2
3	1	3
4	1	4
5	1	5
6	1	6
7	2	1
8	2	6
9	1	7
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.roles (id, name, code, description, is_active) FROM stdin;
1	System Admin	system_admin	Bootstrap system administrator role.	t
2	admin1	admin1	admin1	t
\.


--
-- Data for Name: seats; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.seats (id, room_id, seat_code, seat_label, is_active, is_window_side, has_power_socket, has_track_socket, created_at, updated_at) FROM stdin;
1	1	A-c9b4	Postgres Seat	t	t	t	f	2026-04-20 07:03:31.473293+00	2026-04-20 07:03:31.473296+00
2	1	2	kk	t	f	f	f	2026-04-21 02:11:07.437608+00	2026-04-21 02:11:07.43761+00
3	7	MANUAL-20260429-01-NORMAL	MANUAL-20260429-01-NORMAL	t	t	f	f	2026-04-29 08:49:44.310348+00	2026-04-29 08:49:44.310355+00
4	7	MANUAL-20260429-01-NOSHOW	MANUAL-20260429-01-NOSHOW	t	f	t	f	2026-04-29 08:50:18.522027+00	2026-04-29 08:50:18.522033+00
\.


--
-- Data for Name: study_rooms; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.study_rooms (id, name, location, department_id, is_department_only, is_active, open_time, close_time, created_at, updated_at) FROM stdin;
1	Postgres Room c9b4779b	Building A 301	1	t	t	08:00:00	22:00:00	2026-04-20 07:03:31.470786+00	2026-04-20 07:03:31.47079+00
2			\N	f	f	08:00:00	22:00:00	2026-04-20 08:13:58.912529+00	2026-04-20 08:14:16.227659+00
6	自习室1	北校区3号楼	\N	f	t	08:00:00	22:00:00	2026-04-20 09:12:50.365158+00	2026-04-20 09:12:50.365165+00
7	MANUAL-20260429-01-ROOM	手动验收楼 101	2	t	t	08:00:00	22:00:00	2026-04-29 08:47:02.154079+00	2026-04-29 08:47:02.154085+00
\.


--
-- Data for Name: system_configs; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.system_configs (id, config_key, config_value, value_type, description, updated_at) FROM stdin;
1	max_reservation_hours	4	int	Maximum reservation duration in hours.	2026-04-20 07:03:31.631211+00
2	checkin_grace_minutes	10	int	Allowed check-in grace period in minutes.	2026-04-20 07:03:31.631215+00
3	violation_threshold_minutes	15	int	Violation threshold after missed check-in in minutes.	2026-04-20 07:03:31.631215+00
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.user_roles (id, user_id, role_id) FROM stdin;
1	2	1
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.users (id, student_no, name, email, password_hash, department_id, is_active, last_login_at, created_at, updated_at) FROM stdin;
4	MANUAL-20260429-01-STU	MANUAL-20260429-01-学生	molanyu2001@gmail.com	pbkdf2_sha256$390000$TN0U28Y-Xn9ihRtbpV8O4Q$KX0pAtG6KRNpQfrhlGePUjaB_ncMEpJHKYYTHYGqXCY	2	t	2026-05-06 09:59:02.135721	2026-04-29 08:46:11.585717+00	2026-05-06 09:59:02.138169+00
2	\N	admin	admin	pbkdf2_sha256$390000$DGofgVbR63h8NMbs8w-lBg$8aph9MZlvkj0jtxPFsnxpk7TVGUDow1l_J6ZjPwMGWo	\N	t	2026-06-01 07:29:40.814381	2026-04-20 08:08:55.679568+00	2026-06-01 07:29:40.816719+00
3	123	张三	\N	pbkdf2_sha256$390000$vunQolk_w2t6fLNCZb6THA$syevY1Xik_EnKSBWlmPb05AMoS1ZwvCgLb6whJN3CTo	1	t	2026-04-22 02:30:51.886313	2026-04-22 02:29:51.758723+00	2026-04-22 02:30:51.88701+00
1	PGc9b4779b	Postgres Student	3329727682@qq.com	pbkdf2_sha256$390000$lOkJ66R7iNy0wtdRs1zrwA$JagrRoD2xoF-LezoT70ye9bEMuUZvoUrmR-gfv3_mVs	1	t	2026-04-21 02:53:00.948087	2026-04-20 07:03:31.465732+00	2026-04-21 02:53:00.949059+00
\.


--
-- Data for Name: violation_records; Type: TABLE DATA; Schema: public; Owner: spm
--

COPY public.violation_records (id, user_id, reservation_id, violation_type, occurred_at, remark, created_at) FROM stdin;
1	4	4	NO_SHOW_TIMEOUT	2026-05-06 17:35:00	\N	2026-05-06 17:35:01.75001
2	4	3	NO_SHOW_TIMEOUT	2026-05-06 17:35:00	\N	2026-05-06 17:35:01.761606
3	4	5	NO_SHOW_TIMEOUT	2026-05-06 17:35:00	\N	2026-05-06 17:35:01.76867
4	4	7	NO_SHOW_TIMEOUT	2026-05-06 17:35:00	\N	2026-05-06 17:35:01.775421
\.


--
-- Name: checkin_codes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.checkin_codes_id_seq', 1, true);


--
-- Name: checkin_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.checkin_records_id_seq', 1, true);


--
-- Name: departments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.departments_id_seq', 2, true);


--
-- Name: notification_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.notification_logs_id_seq', 6, true);


--
-- Name: permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.permissions_id_seq', 7, true);


--
-- Name: reservations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.reservations_id_seq', 7, true);


--
-- Name: role_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.role_permissions_id_seq', 9, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.roles_id_seq', 2, true);


--
-- Name: seats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.seats_id_seq', 4, true);


--
-- Name: study_rooms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.study_rooms_id_seq', 7, true);


--
-- Name: system_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.system_configs_id_seq', 3, true);


--
-- Name: user_roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.user_roles_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: violation_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: spm
--

SELECT pg_catalog.setval('public.violation_records_id_seq', 4, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: checkin_codes checkin_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_codes
    ADD CONSTRAINT checkin_codes_pkey PRIMARY KEY (id);


--
-- Name: checkin_records checkin_records_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT checkin_records_pkey PRIMARY KEY (id);


--
-- Name: departments departments_code_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_code_key UNIQUE (code);


--
-- Name: departments departments_name_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_name_key UNIQUE (name);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: notification_logs notification_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT notification_logs_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_code_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_code_key UNIQUE (code);


--
-- Name: permissions permissions_name_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_key UNIQUE (name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: reservations reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (id);


--
-- Name: roles roles_code_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: seats seats_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_pkey PRIMARY KEY (id);


--
-- Name: study_rooms study_rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.study_rooms
    ADD CONSTRAINT study_rooms_pkey PRIMARY KEY (id);


--
-- Name: system_configs system_configs_config_key_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_config_key_key UNIQUE (config_key);


--
-- Name: system_configs system_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_pkey PRIMARY KEY (id);


--
-- Name: checkin_codes uq_checkin_codes_room_date; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_codes
    ADD CONSTRAINT uq_checkin_codes_room_date UNIQUE (room_id, code_date);


--
-- Name: checkin_records uq_checkin_records_reservation; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT uq_checkin_records_reservation UNIQUE (reservation_id);


--
-- Name: notification_logs uq_notification_logs_reservation_type; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT uq_notification_logs_reservation_type UNIQUE (reservation_id, notification_type);


--
-- Name: role_permissions uq_role_permissions_role_permission; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT uq_role_permissions_role_permission UNIQUE (role_id, permission_id);


--
-- Name: seats uq_seats_room_code; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT uq_seats_room_code UNIQUE (room_id, seat_code);


--
-- Name: user_roles uq_user_roles_user_role; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id);


--
-- Name: violation_records uq_violation_records_reservation_type; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.violation_records
    ADD CONSTRAINT uq_violation_records_reservation_type UNIQUE (reservation_id, violation_type);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_student_no_key; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_student_no_key UNIQUE (student_no);


--
-- Name: violation_records violation_records_pkey; Type: CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.violation_records
    ADD CONSTRAINT violation_records_pkey PRIMARY KEY (id);


--
-- Name: ix_checkin_codes_code_date; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_codes_code_date ON public.checkin_codes USING btree (code_date);


--
-- Name: ix_checkin_codes_room_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_codes_room_id ON public.checkin_codes USING btree (room_id);


--
-- Name: ix_checkin_records_checkin_at; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_records_checkin_at ON public.checkin_records USING btree (checkin_at);


--
-- Name: ix_checkin_records_reservation_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_records_reservation_id ON public.checkin_records USING btree (reservation_id);


--
-- Name: ix_checkin_records_room_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_records_room_id ON public.checkin_records USING btree (room_id);


--
-- Name: ix_checkin_records_seat_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_records_seat_id ON public.checkin_records USING btree (seat_id);


--
-- Name: ix_checkin_records_user_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_checkin_records_user_id ON public.checkin_records USING btree (user_id);


--
-- Name: ix_departments_code; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_departments_code ON public.departments USING btree (code);


--
-- Name: ix_notification_logs_notification_type; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_notification_logs_notification_type ON public.notification_logs USING btree (notification_type);


--
-- Name: ix_notification_logs_reservation_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_notification_logs_reservation_id ON public.notification_logs USING btree (reservation_id);


--
-- Name: ix_notification_logs_sent_at; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_notification_logs_sent_at ON public.notification_logs USING btree (sent_at);


--
-- Name: ix_notification_logs_status; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_notification_logs_status ON public.notification_logs USING btree (status);


--
-- Name: ix_notification_logs_user_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_notification_logs_user_id ON public.notification_logs USING btree (user_id);


--
-- Name: ix_permissions_code; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_permissions_code ON public.permissions USING btree (code);


--
-- Name: ix_reservations_end_time; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_end_time ON public.reservations USING btree (end_time);


--
-- Name: ix_reservations_room_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_room_id ON public.reservations USING btree (room_id);


--
-- Name: ix_reservations_seat_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_seat_id ON public.reservations USING btree (seat_id);


--
-- Name: ix_reservations_seat_status_time; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_seat_status_time ON public.reservations USING btree (seat_id, status, start_time, end_time);


--
-- Name: ix_reservations_start_time; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_start_time ON public.reservations USING btree (start_time);


--
-- Name: ix_reservations_status; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_status ON public.reservations USING btree (status);


--
-- Name: ix_reservations_user_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_user_id ON public.reservations USING btree (user_id);


--
-- Name: ix_reservations_user_status_time; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_reservations_user_status_time ON public.reservations USING btree (user_id, status, start_time, end_time);


--
-- Name: ix_roles_code; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_roles_code ON public.roles USING btree (code);


--
-- Name: ix_seats_room_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_seats_room_id ON public.seats USING btree (room_id);


--
-- Name: ix_study_rooms_department_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_study_rooms_department_id ON public.study_rooms USING btree (department_id);


--
-- Name: ix_system_configs_config_key; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_system_configs_config_key ON public.system_configs USING btree (config_key);


--
-- Name: ix_users_department_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_users_department_id ON public.users USING btree (department_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_student_no; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_users_student_no ON public.users USING btree (student_no);


--
-- Name: ix_violation_records_occurred_at; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_violation_records_occurred_at ON public.violation_records USING btree (occurred_at);


--
-- Name: ix_violation_records_reservation_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_violation_records_reservation_id ON public.violation_records USING btree (reservation_id);


--
-- Name: ix_violation_records_user_id; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_violation_records_user_id ON public.violation_records USING btree (user_id);


--
-- Name: ix_violation_records_violation_type; Type: INDEX; Schema: public; Owner: spm
--

CREATE INDEX ix_violation_records_violation_type ON public.violation_records USING btree (violation_type);


--
-- Name: checkin_codes checkin_codes_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_codes
    ADD CONSTRAINT checkin_codes_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.study_rooms(id);


--
-- Name: checkin_records checkin_records_reservation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT checkin_records_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES public.reservations(id);


--
-- Name: checkin_records checkin_records_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT checkin_records_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.study_rooms(id);


--
-- Name: checkin_records checkin_records_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT checkin_records_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(id);


--
-- Name: checkin_records checkin_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.checkin_records
    ADD CONSTRAINT checkin_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_logs notification_logs_reservation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT notification_logs_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES public.reservations(id);


--
-- Name: notification_logs notification_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.notification_logs
    ADD CONSTRAINT notification_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reservations reservations_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.study_rooms(id);


--
-- Name: reservations reservations_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(id);


--
-- Name: reservations reservations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id);


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: seats seats_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.study_rooms(id);


--
-- Name: study_rooms study_rooms_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.study_rooms
    ADD CONSTRAINT study_rooms_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: violation_records violation_records_reservation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.violation_records
    ADD CONSTRAINT violation_records_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES public.reservations(id);


--
-- Name: violation_records violation_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: spm
--

ALTER TABLE ONLY public.violation_records
    ADD CONSTRAINT violation_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict kgYPBNmhHwoRmfN71mQnWoxi5h8BPFkcic9fRCjmB9OYkuIbRs4hGIujI7hCZOy

