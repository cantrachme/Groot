from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ai_engine.app.db.database import DATABASE_URL
from ai_engine.app.models import DocumentChunkEmbedding

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = DocumentChunkEmbedding.metadata


def include_object(
    object,
    name,
    type_,
    reflected,
    compare_to,
) -> bool:
    if type_ == "table" and reflected:
        return name == "document_chunk_embeddings"

    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests and embedding maintenance can provide a transaction on the target DB.
    connection = config.attributes.get("connection")
    if connection is not None:
        run_migrations_on_connection(connection)
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        run_migrations_on_connection(connection)


def run_migrations_on_connection(connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
