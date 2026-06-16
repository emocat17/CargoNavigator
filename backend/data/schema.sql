-- CargoNavigator Bridge Database Schema
-- SQLite (MySQL-compatible subset)
-- Highway network + bridge inventory + influence line data

CREATE TABLE IF NOT EXISTS highways (
    highway_code   TEXT PRIMARY KEY,          -- e.g. G15, G76, S53
    highway_name   TEXT NOT NULL,             -- e.g. 沈海高速, 厦蓉高速
    category       TEXT DEFAULT 'G',           -- G=国道高速, S=省道高速
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS junctions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    junction_name  TEXT NOT NULL UNIQUE,       -- e.g. 港后, 海沧
    junction_type  TEXT DEFAULT '普通',        -- 普通/枢纽
    longitude      REAL NOT NULL,
    latitude       REAL NOT NULL,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS junction_positions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    junction_name  TEXT NOT NULL REFERENCES junctions(junction_name),
    highway_code   TEXT NOT NULL REFERENCES highways(highway_code),
    k_value        REAL NOT NULL,              -- kilometer marker value
    k_string       TEXT,                        -- e.g. k2143
    UNIQUE(junction_name, highway_code)
);

-- Road sections derived from junction positions
-- Each section connects two adjacent junctions on the same highway
CREATE TABLE IF NOT EXISTS road_sections (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    junction_from  TEXT NOT NULL REFERENCES junctions(junction_name),
    junction_to    TEXT NOT NULL REFERENCES junctions(junction_name),
    highway_code   TEXT NOT NULL REFERENCES highways(highway_code),
    k_from         REAL NOT NULL,
    k_to           REAL NOT NULL,
    direction      INTEGER DEFAULT 1            -- 1=ascending K, -1=descending
);

CREATE TABLE IF NOT EXISTS bridges (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    station               TEXT NOT NULL,        -- 桩号 e.g. k0+15
    bridge_type           TEXT,                 -- 桥型 e.g. 变截面连续梁桥
    span                  TEXT,                 -- 跨径 e.g. 40+70+40
    beam_count            REAL,                 -- 梁片数
    lane_count            REAL,                 -- 车道数
    heavy_lane            REAL,                 -- 大件车行驶车道
    control_section       TEXT,                 -- 控制截面
    road_class            TEXT,                 -- 公路等级
    frequency             REAL,                 -- 结构基频 (Hz)
    pos_moment_midas      REAL,                 -- 正弯矩(midas计算)
    neg_moment_midas      REAL,                 -- 负弯矩(midas计算)
    shear_midas           REAL,                 -- 剪力(midas计算)
    pos_moment_design     REAL NOT NULL,        -- 正弯矩设计值
    neg_moment_design     REAL NOT NULL,        -- 负弯矩设计值
    shear_design          REAL NOT NULL,        -- 剪力设计值
    highway_code          TEXT REFERENCES highways(highway_code),  -- nullable: some bridges lack highway data
    data_folder           TEXT,                  -- bridge_data subfolder name
    created_at            TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bridges_station ON bridges(station);
CREATE INDEX IF NOT EXISTS idx_bridges_highway ON bridges(highway_code);
CREATE INDEX IF NOT EXISTS idx_bridges_station_highway ON bridges(station, highway_code);

-- Influence line data from MIDAS
-- Each bridge has 3 types: pos_moment, neg_moment, shear
CREATE TABLE IF NOT EXISTS bridge_influence_lines (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id      INTEGER NOT NULL REFERENCES bridges(id),
    line_type      TEXT NOT NULL,               -- 'pos_moment' | 'neg_moment' | 'shear'
    elem           INTEGER NOT NULL,           -- element number
    position       REAL NOT NULL,              -- relative position within element (0-1)
    distance       REAL NOT NULL,              -- absolute distance from start
    influence_val  REAL NOT NULL               -- influence coefficient
);

CREATE INDEX IF NOT EXISTS idx_il_bridge_type ON bridge_influence_lines(bridge_id, line_type);
CREATE INDEX IF NOT EXISTS idx_il_distance ON bridge_influence_lines(bridge_id, line_type, distance);

-- Bridge effect calculation cache
CREATE TABLE IF NOT EXISTS bridge_effect_cache (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    bridge_id         INTEGER NOT NULL REFERENCES bridges(id),
    loads_ton_json    TEXT NOT NULL,             -- JSON: axis loads in tons
    spacings_json     TEXT NOT NULL,             -- JSON: axis spacings in meters
    pos_moment_min    REAL,
    pos_moment_max    REAL,
    neg_moment_min    REAL,
    neg_moment_max    REAL,
    shear_min         REAL,
    shear_max         REAL,
    damping_factor    REAL,
    pos_moment_ratio  TEXT,                      -- "min~max"
    neg_moment_ratio  TEXT,
    shear_ratio       TEXT,
    is_passable       INTEGER DEFAULT 1,         -- 1=passable, 0=fail
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(bridge_id, loads_ton_json, spacings_json)
);

-- View: bridges with full highway info
CREATE VIEW IF NOT EXISTS v_bridge_detail AS
SELECT b.*, h.highway_name, h.category
FROM bridges b
JOIN highways h ON b.highway_code = h.highway_code;

-- View: junction positions with GPS
CREATE VIEW IF NOT EXISTS v_junction_detail AS
SELECT jp.*, j.longitude, j.latitude, j.junction_type
FROM junction_positions jp
JOIN junctions j ON jp.junction_name = j.junction_name;
