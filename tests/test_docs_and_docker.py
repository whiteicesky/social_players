from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_docker_artifacts_exist():
    for filename in ("Dockerfile", "docker-compose.yml", ".dockerignore", "entrypoint.sh", "nginx.conf"):
        assert (PROJECT_ROOT / filename).exists()


def test_dockerfile_and_compose_content():
    dockerfile_text = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose_text = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    ignore_text = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    entrypoint_text = (PROJECT_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert "FROM python:3" in dockerfile_text
    assert "pip install --no-cache-dir -r requirements.txt" in dockerfile_text
    assert "ENTRYPOINT" in dockerfile_text

    assert "web:" in compose_text
    assert "build: ." in compose_text
    assert "8000:8000" in compose_text
    assert "runserver 0.0.0.0:8000" in compose_text
    assert "entrypoint.sh" in compose_text
    assert "./media:/app/media" in compose_text
    assert "nginx:" in compose_text
    assert "8080:80" in compose_text
    assert "nginx.conf" in compose_text

    assert ".venv" in ignore_text
    assert "__pycache__" in ignore_text

    assert "manage.py migrate" in entrypoint_text
    assert 'exec "$@"' in entrypoint_text


def test_readme_covers_setup_and_docker_usage():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    for phrase in [
        "quick start",
        "docker",
        "testing",
        "project structure",
        "features",
        "sqlite",
        "nginx",
        "8080",
    ]:
        assert phrase in readme

    for command in [
        "pip install -r requirements.txt",
        "python manage.py migrate",
        "python manage.py runserver",
        "docker compose build",
        "docker compose up",
        "docker compose run web pytest",
    ]:
        assert command in readme
