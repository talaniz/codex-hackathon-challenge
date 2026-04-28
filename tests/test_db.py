from sqlalchemy import create_engine, inspect, text

from app.db import configure_database, create_db


def test_create_db_upgrades_existing_rule_file_metadata_columns(tmp_path):
    database_path = tmp_path / "existing.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE rule_files ("
                "id INTEGER PRIMARY KEY, "
                "filename VARCHAR(160) NOT NULL, "
                "status VARCHAR(32) NOT NULL, "
                "status_detail TEXT NOT NULL DEFAULT ''"
                ")"
            )
        )

    configure_database(f"sqlite:///{database_path}")
    create_db()

    columns = {column["name"] for column in inspect(create_engine(f"sqlite:///{database_path}")).get_columns("rule_files")}
    assert {"test_filename", "description", "generation_log"} <= columns
