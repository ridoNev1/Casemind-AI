-- Transform staged data into standardized claims view.

DROP TABLE IF EXISTS fkrtl_stage;
CREATE TABLE fkrtl_stage AS
SELECT
    FKL02 AS claim_id,
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
    FKL17 AS dx_primary_label,
    FKL18A AS procedure_code,
    FKL18 AS procedure_label,
    CAST(COALESCE(NULLIF(FKL28, ''), '0') AS DOUBLE) AS amount_claimed,
    CAST(COALESCE(NULLIF(FKL29, ''), '0') AS DOUBLE) AS amount_paid,
    CAST(COALESCE(NULLIF(FKL28, ''), '0') AS DOUBLE) - CAST(COALESCE(NULLIF(FKL29, ''), '0') AS DOUBLE) AS amount_gap,
    PSTV01 AS patient_id_hash,
    PSTV02 AS family_id_hash,
    PSTV15 AS claim_weight,
    CURRENT_TIMESTAMP AS generated_at
FROM staging_fkrtl;

DROP TABLE IF EXISTS dx_secondary_stage;
CREATE TABLE dx_secondary_stage AS
SELECT
    FKL02 AS claim_id,
    LIST(DISTINCT FKL24) AS dx_secondary_codes,
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

DROP TABLE IF EXISTS enriched_stage;
CREATE TABLE enriched_stage AS
SELECT
    f.*,
    ds.dx_secondary_codes,
    ds.comorbidity_count,
    pl.province_name,
    rm.district_name
FROM fkrtl_stage f
LEFT JOIN dx_secondary_stage ds USING (claim_id)
LEFT JOIN region_map_stage rm
    ON rm.district_code = f.district_code
LEFT JOIN province_lookup_stage pl
    ON pl.province_code = f.province_code;

DROP TABLE IF EXISTS with_labels_stage;
CREATE TABLE with_labels_stage AS
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
FROM enriched_stage e;

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
CREATE TABLE claims_normalized AS
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

DROP TABLE IF EXISTS claims_scored;
CREATE TABLE claims_scored AS
SELECT
    *,
    (los <= 1 AND amount_claimed > peer_p90) AS short_stay_high_cost,
    (bpjs_payment_ratio >= 0.95 AND cost_zscore > 2) AS high_cost_full_paid
FROM claims_normalized;
