-- ======================
-- TABLE SOURCE
-- ======================
CREATE TABLE SOURCE (
    id_source SERIAL PRIMARY KEY,
    nom_source VARCHAR(255) NOT NULL,
    type_source VARCHAR(100),
    fiabilite FLOAT
);

ALTER TABLE SOURCE
ADD CONSTRAINT unique_nom_source UNIQUE (nom_source);

-- ======================
-- TABLE DOCUMENT
-- ======================
CREATE TABLE DOCUMENT (
    id_document SERIAL PRIMARY KEY,
    titre VARCHAR(255),
    contenu TEXT NOT NULL,
    date_publication DATE NOT NULL,
    id_source INT REFERENCES SOURCE(id_source)
);

ALTER TABLE DOCUMENT
ADD CONSTRAINT unique_doc UNIQUE (titre, date_publication, id_source);

-- ======================
-- TABLE ACTIF
-- ======================
CREATE TABLE ACTIF (
    id_actif SERIAL PRIMARY KEY,
    nom_actif VARCHAR NOT NULL,
    ticker VARCHAR,
    secteur VARCHAR
);

ALTER TABLE ACTIF
ADD CONSTRAINT unique_ticker UNIQUE (ticker);

-- ======================
-- TABLE CONCERNE
-- ======================
CREATE TABLE CONCERNE (
    id_document INT REFERENCES DOCUMENT(id_document),
    id_actif INT REFERENCES ACTIF(id_actif),
    PRIMARY KEY (id_document, id_actif)
);

-- ======================
-- TABLE ANALYSE_SENTIMENT
-- ======================
CREATE TABLE ANALYSE_SENTIMENT (
    id_analyse SERIAL PRIMARY KEY,
    polarite VARCHAR(50),
    score FLOAT,
    date_analyse TIMESTAMP,
    id_document INT REFERENCES DOCUMENT(id_document),
    id_actif INT REFERENCES ACTIF(id_actif)
);

-- ======================
-- TABLE UTILISATEUR
-- ======================
CREATE TABLE UTILISATEUR (
    id_utilisateur SERIAL PRIMARY KEY,
    nom VARCHAR(100),
    role VARCHAR(50)
);

-- ======================
-- TABLE ALERTE
-- ======================
CREATE TABLE ALERTE (
    id_alerte SERIAL PRIMARY KEY,
    message TEXT,
    date_alerte TIMESTAMP,
    lu BOOLEAN,
    id_analyse INT REFERENCES ANALYSE_SENTIMENT(id_analyse),
    id_utilisateur INT REFERENCES UTILISATEUR(id_utilisateur)
);

-- ======================
-- INSERT SOURCE PAR DEFAUT
-- ======================
INSERT INTO SOURCE (nom_source, type_source, fiabilite)
VALUES ('Yahoo Finance', 'API', 0.95)
ON CONFLICT (nom_source) DO NOTHING;
