#!/usr/bin/env python3
"""Build a reproducible release ZIP from the validated, explicit file list."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from validate import FILES, ROOT, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="ZIP destination (default: dist/wimbly-<version>.zip)",
    )
    parser.add_argument(
        "--tag", help="Require a release tag matching the manifest version"
    )
    args = parser.parse_args()
    version = validate()
    if args.tag is not None and args.tag != f"v{version}":
        raise ValueError(f"Tag {args.tag} does not match manifest version {version}")
    destination = (args.output or ROOT / "dist" / f"wimbly-{version}.zip").resolve()
    if destination.suffix != ".zip" or destination in (ROOT / name for name in FILES):
        raise ValueError("Choose a .zip destination outside the release file list")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(
        destination, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(FILES):
            info = ZipInfo(f"wimbly/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                (ROOT / name).read_bytes(),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )
    print(f"Packaged Wimbly {version}: {len(FILES)} files, {destination}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Packaging failed: {error}")
