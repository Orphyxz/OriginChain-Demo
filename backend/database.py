import os
import sqlite3
from pathlib import Path
from typing import Any

from .metadata_hash import canonical_metadata, product_metadata


DEFAULT_DB_PATH = Path(__file__).with_name("originchain_demo.sqlite3")


class ProductRepository:
    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self.db_path = Path(db_path or os.environ.get("ORIGINCHAIN_DB_PATH", DEFAULT_DB_PATH))

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    product_code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    batch_number TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    product_key TEXT NOT NULL,
                    metadata_hash TEXT NOT NULL,
                    registration_tx_hash TEXT NOT NULL,
                    registration_block_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ownership_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT NOT NULL,
                    from_role TEXT NOT NULL,
                    from_address TEXT NOT NULL,
                    to_role TEXT NOT NULL,
                    to_address TEXT NOT NULL,
                    transaction_hash TEXT NOT NULL,
                    block_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_code) REFERENCES products(product_code)
                )
                """
            )

    def create_product(self, product: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO products (
                    product_code,
                    name,
                    brand,
                    batch_number,
                    description,
                    metadata_json,
                    product_key,
                    metadata_hash,
                    registration_tx_hash,
                    registration_block_number
                ) VALUES (
                    :product_code,
                    :name,
                    :brand,
                    :batch_number,
                    :description,
                    :metadata_json,
                    :product_key,
                    :metadata_hash,
                    :registration_tx_hash,
                    :registration_block_number
                )
                """,
                product,
            )

    def get_product(self, product_code: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE product_code = ?",
                (product_code,),
            ).fetchone()
        return dict(row) if row else None

    def add_transfer(self, transfer: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO ownership_transfers (
                    product_code,
                    from_role,
                    from_address,
                    to_role,
                    to_address,
                    transaction_hash,
                    block_number
                ) VALUES (
                    :product_code,
                    :from_role,
                    :from_address,
                    :to_role,
                    :to_address,
                    :transaction_hash,
                    :block_number
                )
                """,
                transfer,
            )

    def tamper_product(self, product_code: str) -> dict[str, Any] | None:
        product = self.get_product(product_code)
        if not product:
            return None

        tampered_brand = f"{product['brand']} - ALTERED"
        tampered_description = f"{product['description']} (DEMO TAMPERED OFF-CHAIN)"
        current_metadata = product_metadata(
            product_code=product["product_code"],
            name=product["name"],
            brand=tampered_brand,
            batch_number=product["batch_number"],
            description=tampered_description,
        )

        with self.connect() as connection:
            connection.execute(
                """
                UPDATE products
                SET brand = ?,
                    description = ?,
                    metadata_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_code = ?
                """,
                (
                    tampered_brand,
                    tampered_description,
                    canonical_metadata(current_metadata),
                    product_code,
                ),
            )

        return self.get_product(product_code)

    def reset_demo(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM ownership_transfers")
            connection.execute("DELETE FROM products")
