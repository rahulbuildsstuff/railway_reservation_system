-- ============================================================================
-- RAILWAY RESERVATION SYSTEM (RRS) - 3NF RELATIONAL DATABASE SCHEMA (DDL)
-- Student: Nalla Rahul (00814803124) | B.Tech IT 5th Sem | MAIT | CIC-357
-- ============================================================================

CREATE TABLE IF NOT EXISTS Trains (
    train_no VARCHAR(10) PRIMARY KEY,
    train_name VARCHAR(100) NOT NULL,
    source_station VARCHAR(50) NOT NULL,
    dest_station VARCHAR(50) NOT NULL,
    departure_time VARCHAR(10) NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    available_berths INT NOT NULL DEFAULT 6 CHECK (available_berths >= 0),
    rac_limit INT NOT NULL DEFAULT 2,
    wl_limit INT NOT NULL DEFAULT 3,
    base_fare DECIMAL(10, 2) NOT NULL CHECK (base_fare > 0),
    chart_prepared INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Passengers (
    passenger_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    age INT NOT NULL CHECK (age > 0),
    gender VARCHAR(10) NOT NULL,
    berth_pref VARCHAR(10) DEFAULT 'LB'
);

CREATE TABLE IF NOT EXISTS PNR_Tickets (
    pnr_no VARCHAR(10) PRIMARY KEY,
    train_no VARCHAR(10) NOT NULL,
    primary_passenger VARCHAR(100) NOT NULL,
    pax_count INT NOT NULL CHECK (pax_count BETWEEN 1 AND 6),
    journey_date VARCHAR(15) NOT NULL,
    coach_class VARCHAR(5) NOT NULL,
    quota VARCHAR(15) NOT NULL DEFAULT 'GENERAL',
    booking_status VARCHAR(15) NOT NULL,
    berth_allotted VARCHAR(40),
    fare_amount DECIMAL(10, 2) NOT NULL CHECK (fare_amount >= 0),
    refund_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.0,
    txn_id VARCHAR(25) NOT NULL,
    booking_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (train_no) REFERENCES Trains(train_no)
);
