import argparse
import json
import os
from pathlib import Path

import duckdb
import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
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


def main(config_path: Path) -> None:
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

    con.close()
    print("Pipeline completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build claims_normalized dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to ETL config YAML.")
    args = parser.parse_args()
    main(args.config)
