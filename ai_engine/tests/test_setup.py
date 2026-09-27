import contextlib
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from dotenv import load_dotenv
from sqlalchemy import make_url
from sqlalchemy.exc import OperationalError

from ai_engine.app.db import check


ROOT = Path(__file__).resolve().parents[2]


class EnvironmentSetupTests(unittest.TestCase):
    def load_settings(self, environment, dotenv_text=""):
        """Use a synthetic .env; never read or print developer credentials."""
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / ".env"
            fixture.write_text(dotenv_text)

            def load_fixture(path, **kwargs):
                self.assertEqual(path, ROOT / ".env")
                self.assertEqual(kwargs, {"override": False})
                return load_dotenv(fixture, **kwargs)

            with patch.dict(os.environ, environment, clear=True):
                with patch("dotenv.load_dotenv", side_effect=load_fixture):
                    django = runpy.run_path(str(ROOT / "backend/config/settings_base.py"))
                    ai = runpy.run_path(str(ROOT / "ai_engine/app/db/database.py"))
                ai["engine"].dispose()
        return django, make_url(ai["DATABASE_URL"])

    def assert_database_matches(self, django, url):
        database = django["DATABASES"]["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(database["NAME"], url.database)
        self.assertEqual(database["USER"], url.username)
        self.assertEqual(database["PASSWORD"], url.password)
        self.assertEqual(database["HOST"], url.host)
        self.assertEqual(int(database["PORT"]), url.port)

    def test_services_keep_matching_local_defaults(self):
        django, url = self.load_settings({})
        self.assert_database_matches(django, url)
        self.assertEqual(url.database, "groot_db")
        self.assertEqual(url.username, "rachit")
        self.assertEqual(url.password, "")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 5432)
        self.assertEqual(django["CELERY_BROKER_URL"], "redis://127.0.0.1:6379/0")
        self.assertEqual(django["CELERY_RESULT_BACKEND"], "redis://127.0.0.1:6379/1")

    def test_services_read_repository_dotenv(self):
        django, url = self.load_settings({}, (
            "POSTGRES_DB=fixture_db\nPOSTGRES_USER=fixture_user\n"
            "POSTGRES_PASSWORD=fixture_password\nPOSTGRES_HOST=fixture_host\n"
            "POSTGRES_PORT=5439\nCELERY_BROKER_URL=redis://fixture:6379/2\n"
            "CELERY_RESULT_BACKEND=redis://fixture:6379/3\n"
        ))
        self.assert_database_matches(django, url)
        self.assertEqual(url.database, "fixture_db")
        self.assertEqual(url.port, 5439)
        self.assertEqual(django["CELERY_BROKER_URL"], "redis://fixture:6379/2")
        self.assertEqual(django["CELERY_RESULT_BACKEND"], "redis://fixture:6379/3")

    def test_process_environment_overrides_dotenv_and_preserves_url_characters(self):
        environment = {
            "POSTGRES_DB": "team_db",
            "POSTGRES_USER": "team@user",
            "POSTGRES_PASSWORD": "p@ss:/?#%word",
            "POSTGRES_HOST": "db.internal",
            "POSTGRES_PORT": "5544",
            "CELERY_BROKER_URL": "redis://queue:6379/4",
            "CELERY_RESULT_BACKEND": "redis://queue:6379/5",
        }
        fixture = "\n".join(f"{key}=ignored" for key in environment)
        django, url = self.load_settings(environment, fixture)
        self.assert_database_matches(django, url)
        self.assertEqual(url.database, environment["POSTGRES_DB"])
        self.assertEqual(url.username, environment["POSTGRES_USER"])
        self.assertEqual(url.password, environment["POSTGRES_PASSWORD"])
        self.assertEqual(url.port, 5544)
        self.assertEqual(django["CELERY_BROKER_URL"], environment["CELERY_BROKER_URL"])
        self.assertEqual(django["CELERY_RESULT_BACKEND"], environment["CELERY_RESULT_BACKEND"])

    def test_configuration_ignores_dotenv_in_launch_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text("GROOT_DECOY_ENV=wrong_directory\n")
            code = (
                "import os, runpy; "
                f"runpy.run_path({str(ROOT / 'backend/config/settings_base.py')!r}); "
                f"runpy.run_path({str(ROOT / 'ai_engine/app/db/database.py')!r}); "
                "assert 'GROOT_DECOY_ENV' not in os.environ"
            )
            result = subprocess.run(
                [sys.executable, "-c", code], cwd=directory,
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_alembic_offline_sql_accepts_special_credentials(self):
        environment = {
            **os.environ,
            "POSTGRES_USER": "user@team",
            "POSTGRES_PASSWORD": "p@ss:/?#%word",
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "ai_engine/alembic.ini",
             "upgrade", "head", "--sql"],
            cwd=ROOT, env=environment, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE TABLE document_chunk_embeddings", result.stdout)
        self.assertNotIn("DROP TABLE core_", result.stdout)


class DatabasePreflightTests(unittest.TestCase):
    def test_enabled_vector_returns_version_with_read_only_query(self):
        connection = Mock()
        connection.execute.return_value.scalar_one_or_none.return_value = "0.8.2"
        self.assertEqual(check.check_pgvector(connection), "0.8.2")
        connection.execute.assert_called_once()
        self.assertEqual(
            str(connection.execute.call_args.args[0]),
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'",
        )

    def test_available_but_disabled_vector_has_enable_instruction(self):
        connection = Mock()
        connection.execute.return_value.scalar_one_or_none.side_effect = [None, "0.8.2"]
        with self.assertRaisesRegex(check.DatabasePrerequisiteError, "CREATE EXTENSION"):
            check.check_pgvector(connection)
        self.assertEqual(connection.execute.call_count, 2)
        self.assertTrue(all(str(call.args[0]).startswith("SELECT ")
                            for call in connection.execute.call_args_list))

    def test_missing_server_extension_has_install_instruction(self):
        connection = Mock()
        connection.execute.return_value.scalar_one_or_none.return_value = None
        with self.assertRaisesRegex(check.DatabasePrerequisiteError, "Install pgvector"):
            check.check_pgvector(connection)

    def test_cli_success_and_connection_cleanup(self):
        with patch.object(check, "engine") as engine:
            connection = engine.connect.return_value.__enter__.return_value
            connection.execute.return_value.scalar_one_or_none.return_value = "0.8.2"
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(check.main(), 0)
            engine.connect.return_value.__exit__.assert_called_once()
        self.assertIn("pgvector 0.8.2 is enabled", output.getvalue())

    def test_cli_reports_prerequisite_failure(self):
        with patch.object(check, "engine") as engine:
            connection = engine.connect.return_value.__enter__.return_value
            connection.execute.return_value.scalar_one_or_none.return_value = None
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(check.main(), 1)
        self.assertIn("Install pgvector", output.getvalue())

    def test_cli_connection_error_does_not_disclose_driver_details(self):
        with patch.object(check, "engine") as engine:
            engine.connect.side_effect = OperationalError(
                "connect", {}, Exception("secret-password")
            )
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(check.main(), 1)
        self.assertIn("POSTGRES_*", output.getvalue())
        self.assertNotIn("secret-password", output.getvalue())


if __name__ == "__main__":
    unittest.main()
