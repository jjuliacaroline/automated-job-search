from __future__ import annotations

import base64
import csv
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


NAME = "automated-job-search"
NORMALIZED_NAME = "automated_job_search"
VERSION = "0.1.0"
TAG = "py3-none-any"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"

REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / NORMALIZED_NAME
ROOT_CONFIG_DIR = REPO_ROOT / "config"


def _metadata() -> str:
    return "\n".join(
        [
            "Metadata-Version: 2.1",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: CLI MVP for Finland environmental job search links",
            "Requires-Python: >=3.11",
            "",
        ]
    )


def _wheel_file_name() -> str:
    return f"{NORMALIZED_NAME}-{VERSION}-{TAG}.whl"


def _dist_info_files(editable: bool) -> dict[str, bytes]:
    files = {
        f"{DIST_INFO}/METADATA": _metadata().encode("utf-8"),
        f"{DIST_INFO}/WHEEL": "\n".join(
            [
                "Wheel-Version: 1.0",
                "Generator: build_backend",
                "Root-Is-Purelib: true",
                f"Tag: {TAG}",
                "",
            ]
        ).encode("utf-8"),
        f"{DIST_INFO}/entry_points.txt": "\n".join(
            [
                "[console_scripts]",
                "automated-job-search = automated_job_search.cli:main",
                "",
            ]
        ).encode("utf-8"),
    }
    if editable:
        files[f"{DIST_INFO}/editable.txt"] = b"editable install uses a .pth file\n"
    return files


def _hash_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _add_record_entry(rows: list[tuple[str, str, str]], path: str, data: bytes) -> None:
    rows.append((path, _hash_bytes(data), str(len(data))))


def _package_file_entries(editable: bool) -> dict[str, bytes]:
    if editable:
        return {}

    files: dict[str, bytes] = {}
    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = path.relative_to(SRC_ROOT).as_posix()
        files[relative] = path.read_bytes()

    for path in ROOT_CONFIG_DIR.glob("*.json"):
        relative = f"{NORMALIZED_NAME}/default_config/{path.name}"
        files[relative] = path.read_bytes()

    return files


def _editable_pth() -> tuple[str, bytes]:
    content = f"{SRC_ROOT.as_posix()}\n".encode("utf-8")
    return f"{NORMALIZED_NAME}.pth", content


def _write_wheel_file(wheel_directory: str, editable: bool) -> str:
    wheel_path = Path(wheel_directory) / _wheel_file_name()
    files = _package_file_entries(editable)
    dist_info_files = _dist_info_files(editable)
    record_rows: list[tuple[str, str, str]] = []

    if editable:
        pth_name, pth_data = _editable_pth()
        files[pth_name] = pth_data

    with ZipFile(wheel_path, "w", compression=ZIP_DEFLATED) as archive:
        for relative_path, data in {**files, **dist_info_files}.items():
            archive.writestr(relative_path, data)
            _add_record_entry(record_rows, relative_path, data)

        record_path = f"{DIST_INFO}/RECORD"
        from io import StringIO

        record_stream = StringIO()
        writer = csv.writer(record_stream, lineterminator="\n")
        for row in record_rows:
            writer.writerow(row)
        writer.writerow((record_path, "", ""))
        record_data = record_stream.getvalue().encode("utf-8")
        archive.writestr(record_path, record_data)

    return wheel_path.name


def get_requires_for_build_wheel(config_settings=None):  # noqa: D401, ARG001
    return []


def get_requires_for_build_editable(config_settings=None):  # noqa: D401, ARG001
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):  # noqa: D401, ARG001
    dist_info_dir = Path(metadata_directory) / DIST_INFO
    dist_info_dir.mkdir(parents=True, exist_ok=True)
    (dist_info_dir / "METADATA").write_text(_metadata(), encoding="utf-8")
    (dist_info_dir / "WHEEL").write_text(
        "\n".join(
            [
                "Wheel-Version: 1.0",
                "Generator: build_backend",
                "Root-Is-Purelib: true",
                f"Tag: {TAG}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dist_info_dir / "entry_points.txt").write_text(
        "\n".join(
            [
                "[console_scripts]",
                "automated-job-search = automated_job_search.cli:main",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return DIST_INFO


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: D401, ARG001
    return _write_wheel_file(wheel_directory, editable=False)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: D401, ARG001
    return _write_wheel_file(wheel_directory, editable=True)
