# BPJS Sample Data Overview

Dokumentasi ringkas data sampel dan file referensi pada `resource/bpjs_data`. Semua salinan CSV siap pakai tersimpan di `resource/bpjs_data/raw_cleaned`.

## Dataset Utama (Stata ➜ CSV)

### 2015202201_kepesertaan

- Berkas sumber: `resource/bpjs_data/2015202201_kepesertaan.dta`
- CSV siap konsumsi: `resource/bpjs_data/raw_cleaned/2015202201_kepesertaan.csv`
- Jumlah baris: 2,407,300
- Jumlah kolom: 18
- Kolom identitas umum (prefix PSTV): PSTV01, PSTV02, PSTV03, PSTV04, PSTV05, PSTV06, PSTV07, PSTV08, PSTV09, PSTV10, PSTV11, PSTV12, PSTV13, PSTV14, PSTV15, PSTV16, PSTV17, PSTV18
- Tipe kolom:
  - `PSTV01`: int32
  - `PSTV02`: int32
  - `PSTV03`: datetime64[ns]
  - `PSTV04`: int8
  - `PSTV05`: int8
  - `PSTV06`: int8
  - `PSTV07`: int8
  - `PSTV08`: int8
  - `PSTV09`: int8
  - `PSTV10`: int16
  - `PSTV11`: int8
  - `PSTV12`: int8
  - `PSTV13`: int8
  - `PSTV14`: int16
  - `PSTV15`: float32
  - `PSTV16`: int16
  - `PSTV17`: int8
  - `PSTV18`: float64
- Contoh 5 baris pertama:

```text
 PSTV01   PSTV02     PSTV03  PSTV04  PSTV05  PSTV06  PSTV07  PSTV08  PSTV09  PSTV10  PSTV11  PSTV12  PSTV13  PSTV14    PSTV15  PSTV16  PSTV17  PSTV18
     15       15 1944-03-01       1       2       9       3       2      72    7206       3       1      72    7206 40.024914    2016      99     NaN
     64       64 1971-12-10       1       2       2       3       3      76    7603       3       1      76    7603 36.453136    2016       3     NaN
    101      101 1967-12-31       1       1       2       2       5      12    1273       9       2      12    1273  4.113659    2017       3     NaN
    218      218 1961-01-30       1       2       3       3       2      18    1801       3       1      18    1801 22.901394    2016       1     NaN
    340 70225684 1991-05-31       3       2       2       2       5      33    3311       9       2      33    3311  8.719338    2016       2  2019.0
```

### 202202_fktpkapitasi

- Berkas sumber: `resource/bpjs_data/202202_fktpkapitasi.dta`
- CSV siap konsumsi: `resource/bpjs_data/raw_cleaned/202202_fktpkapitasi.csv`
- Jumlah baris: 3,164,742
- Jumlah kolom: 26
- Kolom identitas umum (prefix PSTV): PSTV01, PSTV02, PSTV15
- Tipe kolom:
  - `PSTV01`: int32
  - `PSTV02`: int32
  - `PSTV15`: float32
  - `FKP02`: object
  - `FKP03`: datetime64[ns]
  - `FKP04`: datetime64[ns]
  - `FKP05`: int8
  - `FKP06`: int16
  - `FKP07`: int8
  - `FKP08`: int8
  - `FKP09`: int8
  - `FKP10`: int8
  - `FKP11`: float64
  - `FKP12`: int8
  - `FKP13`: int8
  - `FKP14`: int16
  - `FKP14A`: object
  - `FKP15`: object
  - `FKP15A`: object
  - `FKP16`: int8
  - `FKP17`: int16
  - `FKP18`: int8
  - `FKP19`: int8
  - `FKP20`: int8
  - `FKP21`: int16
  - `FKP22`: int8
- Contoh 5 baris pertama:

```text
   PSTV01    PSTV02    PSTV15      FKP02      FKP03      FKP04  FKP05  FKP06  FKP07  FKP08  FKP09  FKP10  FKP11  FKP12  FKP13  FKP14 FKP14A FKP15 FKP15A  FKP16  FKP17  FKP18  FKP19  FKP20  FKP21  FKP22
271729140 356137982 93.703957 2075848415 2022-10-28 2022-10-28     35   3502      3      1      3      1   13.0      3     98   9999         9999   9999     98   9998     98     98     98     98      2
466224777 466185771  1.088094 1948594552 2022-07-23 2022-07-23     35   3525      9      2      1      1   13.0      4     98   9999         9999   9999     98   9998     98     98     98     98      2
 15065842  73572995  2.101045 1796903943 2022-02-28 2022-02-28     21   2171      3      1      3      1   13.0      2     98   9999         9999   9999     98   9998     98     98     98     98      2
 36026823  36026823 23.216551 1828888401 2022-03-31 2022-03-31     11   1173      9      2      1      1   28.0      5     98   9999         9999   9999     98   9998     98     98     98     98      2
103468526 160979412  9.349652 2088607536 2022-11-11 2022-11-11     11   1107      9      2      1      1   28.0      2     98   9999         9999   9999     98   9998     98     98     98     98      2
```

### 202203_fkrtl

- Berkas sumber: `resource/bpjs_data/202203_fkrtl.dta`
- CSV siap konsumsi: `resource/bpjs_data/raw_cleaned/202203_fkrtl.csv`
- Jumlah baris: 1,176,438
- Jumlah kolom: 55
- Kolom identitas umum (prefix PSTV): PSTV01, PSTV02, PSTV15
- Tipe kolom:
  - `PSTV01`: int32
  - `PSTV02`: int32
  - `PSTV15`: float32
  - `FKP02`: object
  - `FKL02`: object
  - `FKL03`: datetime64[ns]
  - `FKL04`: datetime64[ns]
  - `FKL05`: int8
  - `FKL06`: int16
  - `FKL07`: int8
  - `FKL08`: int8
  - `FKL09`: int8
  - `FKL10`: int8
  - `FKL11`: int16
  - `FKL12`: int8
  - `FKL13`: int8
  - `FKL14`: int8
  - `FKL15`: int16
  - `FKL15A`: object
  - `FKL16`: object
  - `FKL16A`: object
  - `FKL17`: int16
  - `FKL17A`: object
  - `FKL18`: object
  - `FKL18A`: object
  - `FKL19`: object
  - `FKL19A`: object
  - `FKL20`: int8
  - `FKL21`: int8
  - `FKL22`: int8
  - `FKL23`: int8
  - `FKL25`: int8
  - `FKL26`: int16
  - `FKL27`: int8
  - `FKL28`: int8
  - `FKL29`: int8
  - `FKL30`: object
  - `FKL31`: int8
  - `FKL32`: int32
  - `FKL33`: object
  - `FKL34`: int32
  - `FKL35`: object
  - `FKL36`: object
  - `FKL37`: int32
  - `FKL38`: object
  - `FKL39`: object
  - `FKL40`: int32
  - `FKL41`: object
  - `FKL42`: object
  - `FKL43`: int32
  - `FKL44`: object
  - `FKL45`: object
  - `FKL46`: int32
  - `FKL47`: int32
  - `FKL48`: float64
- Contoh 5 baris pertama:

```text
   PSTV01    PSTV02    PSTV15 FKP02            FKL02      FKL03      FKL04  FKL05  FKL06  FKL07  FKL08  FKL09  FKL10  FKL11  FKL12  FKL13  FKL14  FKL15 FKL15A FKL16                                                           FKL16A  FKL17 FKL17A FKL18                                                     FKL18A    FKL19                                                 FKL19A  FKL20  FKL21  FKL22  FKL23  FKL25  FKL26  FKL27  FKL28  FKL29                                                   FKL30  FKL31   FKL32 FKL33  FKL34 FKL35 FKL36  FKL37 FKL38 FKL39  FKL40 FKL41 FKL42  FKL43 FKL44 FKL45  FKL46   FKL47     FKL48
180205299 180205298  3.662519       100080122V000022 2022-01-03 2022-01-03     94   9403      3      1      3      1      7      3      3      1   1262    R06  R060                                                         Dyspnoea    718    J45  J459                                        Asthma, unspecified J-3-13-0                     PROSEDUR TERAPI SALURAN PERNAFASAN     10      3     13      1     94   9403      3      1     30 9394 - Respiratory medication administered by nebulizer      5  327000  NONE      0  NONE            0  NONE            0  NONE            0  NONE            0  327000  327000.0
314289762 314289762 14.453729       100080122V000028 2022-01-02 2022-01-02     94   9403      3      1      3      2    998      4      3      1    125    B50  B509                       Plasmodium falciparum malaria, unspecified    125    B50  B509                 Plasmodium falciparum malaria, unspecified A-4-14-I PENYAKIT INFEKSI BAKTERI DAN  PARASIT LAIN-LAIN RINGAN      1      4     14      2     94   9403      3      2      3           9059 - Other microscopic examination of blood      5 2218100  NONE      0  NONE            0  NONE            0  NONE            0  NONE            0 2218100 2218100.0
385562166 314289762 15.544407       100080122V000029 2022-01-02 2022-01-02     94   9403      3      1      3      2    998      4      3      1    125    B50  B509                       Plasmodium falciparum malaria, unspecified    125    B50  B508 Other severe and complicated Plasmodium falciparum malaria A-4-14-I PENYAKIT INFEKSI BAKTERI DAN  PARASIT LAIN-LAIN RINGAN      1      4     14      2     94   9403      3      2      3           9059 - Other microscopic examination of blood      5 2218100  NONE      0  NONE            0  NONE            0  NONE            0  NONE            0 2218100 2218100.0
 69505864  69505864  2.836411       100080122V000183 2022-01-05 2022-01-05     94   9403      3      1      3      2    998      2      3      1   1308    R57  R571                                               Hypovolaemic shock     10    A09  A099          Gastroenteritis and colitis of unspecified origin K-4-17-I     NYERI ABDOMEN & GASTROENTERITIS LAIN-LAIN (RINGAN)     11      4     17      2     94   9403      3      2      3           9059 - Other microscopic examination of blood      5 1490600  NONE      0  NONE            0  NONE            0  NONE            0  NONE            0 1490600 1490600.0
135231252 135231252  3.361672       100080122V000263 2022-01-07 2022-01-07     94   9403      3      1      3      1     16      2      3      1   1618    Z09  Z098 Follow-up examination after other treatment for other conditions   1650    Z47  Z479                    Orthopaedic follow-up care, unspecified Z-3-27-0                                         PERAWATAN LUKA     23      3     27      1     94   9403      3      1     30            9716 - Replacement of wound packing or drain      5  195000  NONE      0  NONE            0  NONE            0  NONE            0  NONE            0  195000  195000.0
```

### 202204_nonkapitasi

- Berkas sumber: `resource/bpjs_data/202204_nonkapitasi.dta`
- CSV siap konsumsi: `resource/bpjs_data/raw_cleaned/202204_nonkapitasi.csv`
- Jumlah baris: 141,118
- Jumlah kolom: 36
- Kolom identitas umum (prefix PSTV): PSTV01, PSTV02, PSTV15, PSTV03, PSTV04, PSTV05, PSTV06, PSTV07, PSTV08, PSTV09, PSTV10, PSTV11, PSTV12, PSTV13, PSTV14, PSTV16, PSTV17, PSTV18
- Tipe kolom:
  - `PSTV01`: int32
  - `PSTV02`: int32
  - `PSTV15`: float32
  - `PNK02`: object
  - `PNK03`: datetime64[ns]
  - `PNK04`: datetime64[ns]
  - `PNK05`: datetime64[ns]
  - `PNK06`: int8
  - `PNK07`: int16
  - `PNK08`: int8
  - `PNK09`: int8
  - `PNK10`: int8
  - `PNK11`: int8
  - `PNK12`: int8
  - `PNK13`: int16
  - `PNK13A`: object
  - `PNK14`: object
  - `PNK15`: object
  - `PNK16`: int16
  - `PNK17`: int32
  - `PNK18`: int32
  - `PSTV03`: datetime64[ns]
  - `PSTV04`: int8
  - `PSTV05`: int8
  - `PSTV06`: int8
  - `PSTV07`: int8
  - `PSTV08`: int8
  - `PSTV09`: int8
  - `PSTV10`: int16
  - `PSTV11`: int8
  - `PSTV12`: int8
  - `PSTV13`: int8
  - `PSTV14`: int16
  - `PSTV16`: int16
  - `PSTV17`: int8
  - `PSTV18`: float64
- Contoh 5 baris pertama:

```text
   PSTV01    PSTV02    PSTV15            PNK02      PNK03      PNK04      PNK05  PNK06  PNK07  PNK08  PNK09  PNK10  PNK11  PNK12  PNK13 PNK13A PNK14                                    PNK15  PNK16  PNK17  PNK18     PSTV03  PSTV04  PSTV05  PSTV06  PSTV07  PSTV08  PSTV09  PSTV10  PSTV11  PSTV12  PSTV13  PSTV14  PSTV16  PSTV17  PSTV18
468989973 468975388  4.964005 100100822P000024 2022-08-10 2022-08-10 2022-08-10     31    394      3      1      4      2      3    538    O80   O80              Single spontaneous delivery   2013 800000 800000 1991-03-05       3       2       2       3       3      91    9108       3       1      91    9108    2022       1     NaN
468989973 468975388  4.964005 100100822P000028 2022-08-16 2022-08-16 2022-08-16     31    394      3      1      4      1      3    799    Z39  Z392             Routine postpartum follow-up   1028  25000  25000 1991-03-05       3       2       2       3       3      91    9108       3       1      91    9108    2022       1     NaN
468989973 468975388  4.964005 100100922P000013 2022-09-13 2022-09-13 2022-09-13     31    394      3      1      4      1      3    799    Z39  Z392             Routine postpartum follow-up   1030  25000  25000 1991-03-05       3       2       2       3       3      91    9108       3       1      91    9108    2022       1     NaN
101062637 173313666  7.983972 100101022P000019 2022-10-10 2022-10-10 2022-10-10     31    394      3      1      4      1      5    796    Z36   Z36                      Antenatal screening   1023  50000  50000 1988-08-20       3       2       2       1       5      91    9108       3       1      91    9108    2016       1     NaN
310935457 273409317 20.228731 100330822P000627 2022-08-31 2022-08-31 2022-08-31     31    396      3      1      4      2      2    538    O80  O809 Single spontaneous delivery, unspecified   2012 700000 700000 1998-01-05       3       2       2       3       2      12    1215       3       1      12    1215    2020       1     NaN
```

### 202205_diagnosissekunder

- Berkas sumber: `resource/bpjs_data/202205_diagnosissekunder.dta`
- CSV siap konsumsi: `resource/bpjs_data/raw_cleaned/202205_diagnosissekunder.csv`
- Jumlah baris: 1,267,008
- Jumlah kolom: 4
- Tipe kolom:
  - `FKL02`: object
  - `FKL24`: object
  - `FKL24A`: object
  - `FKL24B`: object
- Contoh 5 baris pertama:

```text
           FKL02 FKL24 FKL24A                                                                          FKL24B
100080122V000514   I10    I10                                            I10 Essential (primary) hypertension
100080122V000556 S7280    S72                                                           S72 Fracture of femur
100080122V000696  A162    A16 A16 Respiratory tuberculosis, not confirmed bacteriologically or histologically
100080122V001023  F419    F41                                                     F41 Other anxiety disorders
100080122V001063  O829    O82                                        O82 Single delivery by caesarean section
```

## Definisi Kolom (Metadata 2023)

Label kolom resmi tersedia pada workbook metadata yang sudah dikonversi ke CSV di folder `raw_cleaned`. Tabel di bawah merangkum sebagian entri; rujuk file CSV terkait untuk daftar penuh.

### Kepesertaan

- File definisi lengkap: `resource/bpjs_data/raw_cleaned/2023_metadata_data_sampel_bpjs_kesehatan_1_kepesertaan.csv`

```text
Variable Information Unnamed: 1                                           Unnamed: 2
            Variable   Position                                                Label
              PSTV01          1                                        Nomor peserta
              PSTV02          2                                       Nomor keluarga
              PSTV03          3                                Tanggal lahir peserta
              PSTV04          4                                    Hubungan Keluarga
              PSTV05          5                                        Jenis Kelamin
              PSTV06          6                                    Status perkawinan
              PSTV07          7                                          Kelas rawat
              PSTV08          8                                   Segmentasi peserta
              PSTV09          9                      Provinsi Tempat Tinggal Peserta
              PSTV10         10                Kabupaten/Kota Tempat Tinggal Peserta
              PSTV11         11                                   Kepemilikan faskes
              PSTV12         12                                         Jenis faskes
              PSTV13         13       Provinsi Fasilitas Kesehatan Peserta Terdaftar
              PSTV14         14 Kabupaten/Kota Fasilitas Kesehatan Peserta Terdaftar
```

### FKTP

- File definisi lengkap: `resource/bpjs_data/raw_cleaned/2023_metadata_data_sampel_bpjs_kesehatan_2_fktp.csv`

```text
Variable Information Unnamed: 1                             Unnamed: 2
            Variable   Position                                  Label
              PSTV01          1                          Nomor peserta
              PSTV02          2                         Nomor keluarga
              PSTV15          3                                  Bobot
               FKP02          4                      ID Kunjungan FKTP
               FKP03          5          Tanggal datang kunjungan FKTP
               FKP04          6          Tanggal pulang kunjungan FKTP
               FKP05          7                          Provinsi FKTP
               FKP06          8                    Kabupaten/Kota FKTP
               FKP07          9                       Kepemilikan FKTP
               FKP08         10                             Jenis FKTP
               FKP09         11                              Tipe FKTP
               FKP10         12                 Tingkat Pelayanan FKTP
               FKP11         13                        Jenis Poli FKTP
               FKP12         14 Segmen Peserta saat akses layanan FKTP
```

### FKRTL

- File definisi lengkap: `resource/bpjs_data/raw_cleaned/2023_metadata_data_sampel_bpjs_kesehatan_3_fkrtl.csv`

```text
Variable Information Unnamed: 1                          Unnamed: 2
            Variable   Position                               Label
              PSTV01          1                       Nomor peserta
              PSTV02          2                      Nomor keluarga
              PSTV15          3                               Bobot
               FKP02          4 No Asal Rujukan (ID Kunjungan FKTP)
               FKL02          5                        ID Kunjungan
               FKL03          6      Tanggal datang kunjungan FKRTL
               FKL04          7      Tanggal pulang kunjungan FKRTL
               FKL05          8                      Provinsi FKRTL
               FKL06          9                Kabupaten/Kota FKRTL
               FKL07         10                   Kepemilikan FKRTL
               FKL08         11                         Jenis FKRTL
               FKL09         12                          Tipe FKRTL
               FKL10         13             Tingkat Pelayanan FKRTL
               FKL11         14                    Jenis Poli FKRTL
```

### Non Kapitasi

- File definisi lengkap: `resource/bpjs_data/raw_cleaned/2023_metadata_data_sampel_bpjs_kesehatan_4_non_kapitasi.csv`

```text
Variable Information Unnamed: 1           Unnamed: 2
            Variable   Position                Label
              PSTV01          1        Nomor Peserta
              PSTV02          2       Nomor keluarga
              PSTV15          3                Bobot
               PNK02          4         ID Kunjungan
               PNK03          5    Tanggal kunjungan
               PNK04          6     Tanggal tindakan
               PNK05          7       Tanggal pulang
               PNK06          8      Provinsi faskes
               PNK07          9 Kode Kab/Kota faskes
               PNK08         10   Kepemilikan faskes
               PNK09         11         Jenis faskes
               PNK10         12          Tipe faskes
               PNK11         13      Tingkat layanan
               PNK12         14       Segmen peserta
```

### Kode wilayah

- File definisi lengkap: `resource/bpjs_data/raw_cleaned/2023_metadata_data_sampel_bpjs_kesehatan_kode_wilayah.csv`

```text
 kode_prov nama_provinsi  kode_kabupaten/kota nama_kabupaten/kota
      11.0          ACEH                 1101            SIMEULUE
       NaN           NaN                 1102        ACEH SINGKIL
       NaN           NaN                 1103        ACEH SELATAN
       NaN           NaN                 1104       ACEH TENGGARA
       NaN           NaN                 1105          ACEH TIMUR
       NaN           NaN                 1106         ACEH TENGAH
       NaN           NaN                 1107          ACEH BARAT
       NaN           NaN                 1108          ACEH BESAR
       NaN           NaN                 1109               PIDIE
       NaN           NaN                 1110             BIREUEN
       NaN           NaN                 1111          ACEH UTARA
       NaN           NaN                 1112     ACEH BARAT DAYA
       NaN           NaN                 1113           GAYO LUES
       NaN           NaN                 1114        ACEH TAMIANG
       NaN           NaN                 1115          NAGAN RAYA
```

## Kamus Diagnosa ICD-10

Tabel referensi ICD10 tersedia dalam format CSV berikut:

- `resource/bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fkrtl_diagnosis_masuk.csv`
- `resource/bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fkrtl_diagnosis_primer.csv`
- `resource/bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fktp_kapitasi_sheet1.csv`
- `resource/bpjs_data/raw_cleaned/2022_kode_icd10_untuk_diagnosis_fktp_non_kapitasi_sheet1.csv`
