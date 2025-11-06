-- Transform staged data into standardized claims view.

DROP TABLE IF EXISTS fkrtl_stage;
CREATE TABLE fkrtl_stage AS
SELECT
    FKL02 AS claim_id,
    FKL06 AS facility_code,
    CAST(FKL03 AS DATE) AS admit_dt,
    CAST(FKL04 AS DATE) AS discharge_dt,
    GREATEST(DATE_DIFF('day', CAST(FKL03 AS DATE), CAST(FKL04 AS DATE)), 0) AS los,
    CAST(COALESCE(NULLIF(FKL05, ''), '0') AS INTEGER) AS province_code,
    CAST(COALESCE(NULLIF(FKL06, ''), '0') AS INTEGER) AS district_code,
    CAST(COALESCE(NULLIF(FKL07, ''), '0') AS INTEGER) AS facility_ownership_code,
    CAST(COALESCE(NULLIF(FKL08, ''), '0') AS INTEGER) AS facility_type_code,
    CAST(COALESCE(NULLIF(FKL09, ''), '0') AS INTEGER) AS facility_class_code,
    CAST(COALESCE(NULLIF(FKL10, ''), '0') AS INTEGER) AS service_level_code,
    CAST(COALESCE(NULLIF(FKL11, ''), '0') AS INTEGER) AS poli_type_code,
    CAST(COALESCE(NULLIF(FKL12, ''), '0') AS INTEGER) AS participant_segment_code,
    CAST(COALESCE(NULLIF(FKL23, ''), '0') AS INTEGER) AS severity_code,
    FKL17A AS dx_primary_code,
    FKL18A AS dx_primary_label,
    FKL19A AS dx_primary_group,
    FKL18A AS procedure_code,
    FKL18 AS procedure_label,
    CAST(COALESCE(NULLIF(FKL28, ''), '0') AS DOUBLE) AS amount_claimed,
    CAST(COALESCE(NULLIF(FKL29, ''), '0') AS DOUBLE) AS amount_paid,
    CAST(COALESCE(NULLIF(FKL28, ''), '0') AS DOUBLE) - CAST(COALESCE(NULLIF(FKL29, ''), '0') AS DOUBLE) AS amount_gap,
    PSTV01 AS patient_id_hash,
    PSTV02 AS family_id_hash,
    sha256(CONCAT('{{ hashing.patient_salt }}', COALESCE(CAST(PSTV01 AS VARCHAR), ''))) AS patient_key,
    sha256(CONCAT('{{ hashing.family_salt }}', COALESCE(CAST(PSTV02 AS VARCHAR), ''))) AS family_key,
    PSTV15 AS claim_weight,
    CURRENT_TIMESTAMP AS generated_at
FROM staging_fkrtl;

DROP TABLE IF EXISTS dx_secondary_stage;
CREATE TABLE dx_secondary_stage AS
SELECT
    FKL02 AS claim_id,
    LIST(DISTINCT FKL24) AS dx_secondary_codes,
    LIST(DISTINCT FKL24B) FILTER (WHERE COALESCE(FKL24B, '') <> '') AS dx_secondary_labels,
    COUNT(*) AS comorbidity_count
FROM staging_diagnosa_sekunder
GROUP BY 1;

DROP TABLE IF EXISTS province_lookup_stage;
CREATE TABLE province_lookup_stage (province_code INTEGER, province_name VARCHAR);
INSERT INTO province_lookup_stage VALUES
    (11, 'ACEH'),
    (12, 'SUMATERA UTARA'),
    (13, 'SUMATERA BARAT'),
    (14, 'RIAU'),
    (15, 'JAMBI'),
    (16, 'SUMATERA SELATAN'),
    (17, 'BENGKULU'),
    (18, 'LAMPUNG'),
    (19, 'KEPULAUAN BANGKA BELITUNG'),
    (21, 'KEPULAUAN RIAU'),
    (31, 'DKI JAKARTA'),
    (32, 'JAWA BARAT'),
    (33, 'JAWA TENGAH'),
    (34, 'DI YOGYAKARTA'),
    (35, 'JAWA TIMUR'),
    (36, 'BANTEN'),
    (51, 'BALI'),
    (52, 'NUSA TENGGARA BARAT'),
    (53, 'NUSA TENGGARA TIMUR'),
    (61, 'KALIMANTAN BARAT'),
    (62, 'KALIMANTAN TENGAH'),
    (63, 'KALIMANTAN SELATAN'),
    (64, 'KALIMANTAN TIMUR'),
    (65, 'KALIMANTAN UTARA'),
    (71, 'SULAWESI UTARA'),
    (72, 'SULAWESI TENGAH'),
    (73, 'SULAWESI SELATAN'),
    (74, 'SULAWESI TENGGARA'),
    (75, 'GORONTALO'),
    (76, 'SULAWESI BARAT'),
    (81, 'MALUKU'),
    (82, 'MALUKU UTARA'),
    (91, 'PAPUA BARAT'),
    (94, 'PAPUA');

DROP TABLE IF EXISTS region_map_stage;
CREATE TABLE region_map_stage AS
SELECT
    CAST("kode_kabupaten/kota" AS INTEGER) AS district_code,
    MAX("nama_kabupaten/kota") AS district_name,
    CAST(MAX(kode_prov) AS INTEGER) AS province_code
FROM staging_region_master
WHERE "kode_kabupaten/kota" IS NOT NULL
GROUP BY "kode_kabupaten/kota";

DROP TABLE IF EXISTS hospital_raw_stage;
CREATE TABLE hospital_raw_stage AS
SELECT *
FROM read_csv_auto('{{ references.hospital_master }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE, DELIM=';');

DROP TABLE IF EXISTS hospital_lookup_stage;
CREATE TABLE hospital_lookup_stage AS
WITH raw AS (
    SELECT
        TRIM(id) AS facility_id,
        UPPER(TRIM(nama)) AS facility_name,
        UPPER(TRIM(propinsi)) AS province_name,
        UPPER(TRIM(kab)) AS district_name,
        UPPER(TRIM(kepemilikan)) AS ownership_raw,
        UPPER(TRIM(jenis)) AS type_raw,
        UPPER(TRIM(kelas)) AS class_raw
    FROM hospital_raw_stage
    WHERE COALESCE(TRIM(id), '') <> ''
)
SELECT
    facility_id,
    facility_name,
    province_name,
    district_name,
    ownership_raw,
    type_raw,
    class_raw,
    CASE
        WHEN ownership_raw LIKE '%VERTIKAL%' THEN 'Vertikal'
        WHEN ownership_raw LIKE '%PEMPROV%' THEN 'Pemprov'
        WHEN ownership_raw LIKE '%PEMKAB%' OR ownership_raw LIKE '%PEMKOT%' THEN 'Pemkab'
        WHEN ownership_raw LIKE '%KEMENTERIAN%' THEN 'Vertikal'
        WHEN ownership_raw LIKE '%BUMN%' THEN 'BUMN'
        WHEN ownership_raw LIKE '%POLRI%' THEN 'POLRI'
        WHEN ownership_raw LIKE '%TNI AL%' THEN 'TNI AL'
        WHEN ownership_raw LIKE '%TNI AU%' THEN 'TNI AU'
        WHEN ownership_raw LIKE '%TNI AD%' OR ownership_raw LIKE '%TNI%' THEN 'TNI AD'
        WHEN ownership_raw LIKE '%SWASTA%' OR ownership_raw LIKE '%YAYASAN%' THEN 'Swasta'
        ELSE 'Lainnya'
    END AS ownership_normalized,
    CASE
        WHEN type_raw LIKE 'RUMAH SAKIT%' OR type_raw LIKE 'RS %' OR type_raw = 'RUMAH SAKIT' THEN 'Rumah Sakit'
        WHEN type_raw LIKE '%KLINIK UTAMA%' THEN 'Klinik Utama'
        WHEN type_raw LIKE '%KLINIK PRATAMA%' THEN 'Klinik Pratama'
        ELSE 'Faskes Lain'
    END AS type_normalized,
    CASE
        WHEN class_raw IN ('A', 'B', 'C', 'D') THEN 'RS Kelas ' || class_raw
        WHEN class_raw LIKE 'KLINIK%' THEN 'Klinik Non Rawat Inap'
        ELSE 'Tidak diketahui'
    END AS class_normalized
FROM raw;

DROP TABLE IF EXISTS hospital_region_stage;
CREATE TABLE hospital_region_stage AS
SELECT
    province_name AS hospital_province_name,
    district_name AS hospital_district_name,
    STRING_AGG(DISTINCT facility_name, '; ' ORDER BY facility_name) AS region_facility_names,
    STRING_AGG(DISTINCT ownership_raw, '; ' ORDER BY ownership_raw) AS region_ownership_names,
    STRING_AGG(DISTINCT type_raw, '; ' ORDER BY type_raw) AS region_facility_type_names,
    STRING_AGG(DISTINCT class_raw, '; ' ORDER BY class_raw) AS region_facility_class_names
FROM hospital_lookup_stage
GROUP BY province_name, district_name;

DROP TABLE IF EXISTS icd10_reference_stage;
CREATE TABLE icd10_reference_stage AS
SELECT DISTINCT
    UPPER(TRIM(ICD10_Code)) AS icd_code,
    TRIM(REGEXP_REPLACE(ICD10_Text, '^[A-Z0-9\\.]+\\s*', '')) AS icd_label
FROM read_csv_auto('resource/private_bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fkrtl_diagnosis_primer.csv', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE)
UNION
SELECT DISTINCT
    UPPER(TRIM(ICD10_Code)) AS icd_code,
    TRIM(REGEXP_REPLACE(ICD10_Text, '^[A-Z0-9\\.]+\\s*', '')) AS icd_label
FROM read_csv_auto('resource/private_bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fkrtl_diagnosis_masuk.csv', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

DROP TABLE IF EXISTS enriched_stage;
CREATE TABLE enriched_stage AS
SELECT
    f.* REPLACE (COALESCE(NULLIF(f.dx_primary_label, ''), ic.icd_label) AS dx_primary_label),
    ds.dx_secondary_codes,
    ds.dx_secondary_labels,
    ds.comorbidity_count,
    pl.province_name,
    rm.district_name,
    hr.region_facility_names,
    hr.region_ownership_names,
    hr.region_facility_type_names,
    hr.region_facility_class_names
FROM fkrtl_stage f
LEFT JOIN dx_secondary_stage ds USING (claim_id)
LEFT JOIN region_map_stage rm
    ON rm.district_code = f.district_code
LEFT JOIN province_lookup_stage pl
    ON pl.province_code = f.province_code
LEFT JOIN hospital_region_stage hr
    ON hr.hospital_province_name = pl.province_name
   AND hr.hospital_district_name = rm.district_name
LEFT JOIN icd10_reference_stage ic
    ON ic.icd_code = COALESCE(NULLIF(f.dx_primary_code, ''), NULLIF(SUBSTR(f.dx_primary_code, 1, 3), ''));

DROP TABLE IF EXISTS with_labels_stage;
CREATE TABLE with_labels_stage AS
WITH base AS (
    SELECT
        e.*,
        CASE facility_ownership_code
            WHEN 1 THEN 'Vertikal'
            WHEN 2 THEN 'Pemprov'
            WHEN 3 THEN 'Pemkab'
            WHEN 4 THEN 'POLRI'
            WHEN 5 THEN 'TNI AD'
            WHEN 6 THEN 'TNI AL'
            WHEN 7 THEN 'TNI AU'
            WHEN 8 THEN 'BUMN'
            WHEN 9 THEN 'Swasta'
            ELSE 'Lainnya'
        END AS facility_ownership,
        CASE facility_type_code
            WHEN 1 THEN 'Rumah Sakit'
            WHEN 2 THEN 'Klinik Utama'
            WHEN 3 THEN 'Klinik Pratama'
            ELSE 'Faskes Lain'
        END AS facility_type,
        CASE facility_class_code
            WHEN 1 THEN 'RS Kelas A'
            WHEN 2 THEN 'RS Kelas B'
            WHEN 3 THEN 'RS Kelas C'
            WHEN 4 THEN 'RS Kelas D'
            WHEN 5 THEN 'RS Swasta Setara Type A'
            WHEN 6 THEN 'RS Swasta Setara Type B'
            WHEN 7 THEN 'RS Swasta Setara Type C'
            WHEN 8 THEN 'RS Swasta Setara Type D'
            WHEN 9 THEN 'RS TNI Polri Kelas I'
            WHEN 10 THEN 'RS TNI Polri Kelas II'
            WHEN 11 THEN 'RS TNI Polri Kelas III'
            WHEN 12 THEN 'RS TNI Polri Kelas IV'
            WHEN 13 THEN 'RS Khusus Bedah'
            WHEN 14 THEN 'RS Khusus Gigi dan Mulut'
            WHEN 15 THEN 'RS Khusus Hemodialisa'
            WHEN 16 THEN 'RS Khusus Ibu dan Anak'
            WHEN 17 THEN 'RS Khusus Jantung'
            WHEN 18 THEN 'RS Khusus Jiwa'
            WHEN 19 THEN 'RS Khusus Kanker Onkologi'
            WHEN 20 THEN 'RS Khusus Kusta'
            WHEN 21 THEN 'RS Khusus Mata'
            WHEN 22 THEN 'RS Khusus Paru'
            WHEN 23 THEN 'RS Khusus Stroke'
            WHEN 24 THEN 'RS Khusus Tulang'
            WHEN 25 THEN 'Klinik Non Rawat Inap'
            WHEN 26 THEN 'RS Khusus Lain'
            WHEN 27 THEN 'RS Non Provider Gawat Darurat'
            ELSE 'Tidak diketahui'
        END AS facility_class,
        CASE service_level_code
            WHEN 1 THEN 'RJTL'
            WHEN 2 THEN 'RITL'
            ELSE 'Unknown'
        END AS service_type,
        CASE severity_code
            WHEN 1 THEN 'ringan'
            WHEN 2 THEN 'sedang'
            WHEN 3 THEN 'berat'
            WHEN 4 THEN 'fatal'
            ELSE 'unknown'
        END AS severity_group
    FROM enriched_stage e
),
matched AS (
    SELECT
        b.claim_id,
        hl.facility_id,
        hl.facility_name,
        hl.class_normalized,
        hl.type_normalized,
        hl.ownership_normalized,
        ROW_NUMBER() OVER (
            PARTITION BY b.claim_id
            ORDER BY
                CASE WHEN hl.facility_id IS NULL THEN 1 ELSE 0 END,
                CASE WHEN hl.class_normalized = b.facility_class THEN 0 ELSE 1 END,
                CASE WHEN hl.type_normalized = b.facility_type THEN 0 ELSE 1 END,
                CASE WHEN hl.ownership_normalized = b.facility_ownership THEN 0 ELSE 1 END,
                hl.facility_name
        ) AS match_rank
    FROM base b
    LEFT JOIN hospital_lookup_stage hl
        ON hl.province_name = b.province_name
       AND hl.district_name = b.district_name
)
SELECT
    b.*,
    m.facility_id,
    CASE
        WHEN m.facility_name IS NOT NULL THEN m.facility_name
        WHEN COALESCE(b.region_facility_names, '') <> '' THEN TRIM(REGEXP_REPLACE(b.region_facility_names, ';.*$', ''))
        ELSE NULL
    END AS facility_name,
    CASE
        WHEN m.facility_id IS NOT NULL THEN 'exact'
        WHEN COALESCE(b.region_facility_names, '') <> '' THEN 'regional'
        ELSE 'unmatched'
    END AS facility_match_quality
FROM base b
LEFT JOIN matched m
    ON b.claim_id = m.claim_id
   AND m.match_rank = 1;

DROP TABLE IF EXISTS peer_group_stage;
CREATE TABLE peer_group_stage AS
SELECT
    claim_id,
    CONCAT_WS(
        '|',
        COALESCE(dx_primary_code, 'UNKNOWN'),
        COALESCE(severity_group, 'unknown'),
        COALESCE(facility_class, 'Tidak diketahui'),
        COALESCE(province_name, 'unknown')
    ) AS peer_key
FROM with_labels_stage;

DROP TABLE IF EXISTS peer_stats_stage;
CREATE TABLE peer_stats_stage AS
SELECT
    pg.peer_key,
    AVG(amount_claimed) AS peer_mean,
    APPROX_QUANTILE(amount_claimed, 0.9) AS peer_p90,
    STDDEV_POP(amount_claimed) AS peer_std
FROM with_labels_stage wl
JOIN peer_group_stage pg USING (claim_id)
GROUP BY 1;

DROP TABLE IF EXISTS claims_normalized;
DROP TABLE IF EXISTS claims_base_stage;
CREATE TABLE claims_base_stage AS
SELECT
    wl.*,
    CASE WHEN amount_claimed > 0 THEN amount_paid / amount_claimed ELSE NULL END AS bpjs_payment_ratio,
    pg.peer_key,
    ps.peer_mean,
    ps.peer_p90,
    ps.peer_std,
    CASE
        WHEN ps.peer_std IS NULL OR ps.peer_std = 0 THEN NULL
        ELSE (wl.amount_claimed - ps.peer_mean) / ps.peer_std
    END AS cost_zscore,
    '{{ ruleset_version }}' AS ruleset_version
FROM with_labels_stage wl
JOIN peer_group_stage pg USING (claim_id)
LEFT JOIN peer_stats_stage ps USING (peer_key);

DROP TABLE IF EXISTS duplicate_flag_stage;
CREATE TABLE duplicate_flag_stage AS
SELECT
    cb.claim_id,
    EXISTS (
        SELECT 1
        FROM claims_base_stage other
        WHERE other.claim_id <> cb.claim_id
          AND other.patient_key = cb.patient_key
          AND other.patient_key IS NOT NULL
          AND COALESCE(other.dx_primary_code, '') = COALESCE(cb.dx_primary_code, '')
          AND COALESCE(other.procedure_code, '') = COALESCE(cb.procedure_code, '')
          AND other.admit_dt IS NOT NULL
          AND cb.admit_dt IS NOT NULL
          AND ABS(DATE_DIFF('day', other.admit_dt, cb.admit_dt)) <= 3
    ) AS duplicate_pattern
FROM claims_base_stage cb;

CREATE TABLE claims_normalized AS
SELECT
    cb.*,
    COALESCE(df.duplicate_pattern, FALSE) AS duplicate_pattern
FROM claims_base_stage cb
LEFT JOIN duplicate_flag_stage df USING (claim_id);

DROP TABLE IF EXISTS claims_scored;
CREATE TABLE claims_scored AS
SELECT
    *,
    (los <= 1 AND amount_claimed > peer_p90) AS short_stay_high_cost,
    (bpjs_payment_ratio >= 0.95 AND cost_zscore > 2) AS high_cost_full_paid
FROM claims_normalized;
