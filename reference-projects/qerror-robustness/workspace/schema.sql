-- JOB-Light-style synthetic schema: PK-FK chain mimicking IMDB subset.
-- Deliberately small (fits in-memory, runs <180s per trial) but preserves the
-- multi-table join structure that makes cardinality estimation non-trivial.
-- Limitation: this is a synthetic schema modeled on JOB-Light, NOT the real
-- IMDB dump. Disclosed in the paper's Limitations section.

CREATE TABLE title (
    id INTEGER PRIMARY KEY,
    kind_id INTEGER,
    production_year INTEGER,
    title_text TEXT
);

CREATE TABLE name (
    id INTEGER PRIMARY KEY,
    gender TEXT,
    name_pname_cf TEXT
);

CREATE TABLE cast_info (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role_id INTEGER,
    nr_order INTEGER,
    FOREIGN KEY (movie_id) REFERENCES title(id),
    FOREIGN KEY (person_id) REFERENCES name(id)
);

CREATE TABLE movie_info (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    info_type_id INTEGER,
    info TEXT,
    FOREIGN KEY (movie_id) REFERENCES title(id)
);

CREATE INDEX idx_cast_movie ON cast_info(movie_id);
CREATE INDEX idx_cast_person ON cast_info(person_id);
CREATE INDEX idx_movieinfo_movie ON movie_info(movie_id);
CREATE INDEX idx_title_kind ON title(kind_id);
CREATE INDEX idx_title_year ON title(production_year);
