import sys
import argparse
import os
from pathlib import Path

import duckdb
import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from ml.common import metadata
from ml.pipelines.refresh_ml_scores import refresh_scores

DEFAULT_CONFIG = ROOT_DIR / "pipelines" / "claims_normalized" / "config.yaml"
SQL_DIR = ROOT_DIR / "pipelines" / "claims_normalized" / "sql"


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def render_sql(template_path: Path, context: dict) -> str:
    sql = template_path.read_text()
    for key, value in context.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                placeholder = f"{{{{ {key}.{sub_key} }}}}"
                sql = sql.replace(placeholder, str(sub_value))
        else:
            placeholder = f"{{{{ {key} }}}}"
            sql = sql.replace(placeholder, str(value))
    return sql


def main(args: argparse.Namespace) -> None:
    config_path = args.config
    config = load_config(config_path)
    duckdb_path = config.get("duckdb_path", "instance/analytics.duckdb")
    os.makedirs(os.path.dirname(duckdb_path), exist_ok=True)

    con = duckdb.connect(duckdb_path)

    staging_sql = render_sql(SQL_DIR / "staging.sql", config)
    transform_sql = render_sql(SQL_DIR / "transform.sql", config)

    print("Executing staging queries...")
    con.execute(staging_sql)

    print("Executing transform queries...")
    con.execute(transform_sql)

    output_dir = Path(config["output"]["parquet_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = output_dir / f"{config['output']['table_name']}.parquet"
    print(f"Exporting claims_normalized to {parquet_path}")
    con.execute(f"COPY (SELECT * FROM claims_normalized) TO '{parquet_path}' (FORMAT PARQUET);")

    print("Updating metadata tables...")
    metadata.ensure_metadata_tables(duckdb_path)
    rows_processed = con.execute("SELECT COUNT(*) FROM claims_normalized").fetchone()[0]
    metadata.record_ruleset_version(duckdb_path, config.get("ruleset_version"), config.get("ruleset_description"))
    metadata.record_etl_run(
        duckdb_path,
        ruleset_version=config.get("ruleset_version"),
        rows_processed=rows_processed,
        notes=f"parquet={parquet_path}",
    )

    con.close()
    print("Pipeline completed successfully.")

    refresh_cfg = config.get("post_refresh_ml", {})
    should_refresh = refresh_cfg.get("enabled", False)
    top_k_default = refresh_cfg.get("top_k")

    if args.refresh_ml is not None:
        should_refresh = args.refresh_ml
    top_k = args.refresh_top_k if args.refresh_top_k is not None else top_k_default

    if should_refresh:
        print("Running ML score refresh...")
        refresh_scores(top_k=top_k, config_path=config_path)
        print("ML score refresh completed.")
    elif top_k is not None:
        print(f"Note: top_k={top_k} provided but refresh not enabled; skipping refresh.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build claims_normalized dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to ETL config YAML.")
    parser.add_argument("--refresh-ml", action="store_true", dest="refresh_ml", help="Set untuk menjalankan refresh skor ML setelah ETL.")
    parser.add_argument("--no-refresh-ml", action="store_false", dest="refresh_ml", help="Set untuk tidak menjalankan refresh ML meskipun config mengaktifkan.")
    parser.add_argument("--refresh-top-k", type=int, default=None, help="Jumlah top-K untuk QC saat refresh ML (override config).")
    parser.set_defaults(refresh_ml=None)
    args = parser.parse_args()
    main(args)
