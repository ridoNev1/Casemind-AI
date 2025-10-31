-- Create staging tables for raw input data.
CREATE OR REPLACE TABLE staging_fkrtl AS
SELECT *
FROM read_csv_auto('{{ sources.fkrtl }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_diagnosa_sekunder AS
SELECT *
FROM read_csv_auto('{{ sources.diagnosa_sekunder }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_kepesertaan AS
SELECT *
FROM read_csv_auto('{{ sources.kepesertaan }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_fktp_kapitasi AS
SELECT *
FROM read_csv_auto('{{ sources.fktp_kapitasi }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_non_kap AS
SELECT *
FROM read_csv_auto('{{ sources.non_kap }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_hospital_master AS
SELECT *
FROM read_csv_auto('{{ references.hospital_master }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);

CREATE OR REPLACE TABLE staging_region_master AS
SELECT *
FROM read_csv_auto('{{ references.region_master }}', HEADER=TRUE, SAMPLE_SIZE=-1, ALL_VARCHAR=TRUE);
