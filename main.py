import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import requests

import java

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s/%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

# constants

OUTPUT_DIR = Path("mc")
OUTPUT_SRC_DIR = OUTPUT_DIR / "src"
CACHE_DIR = Path(".cache/")

ENIGMA_VERSION = "2.5.2"
ENIGMA_PATH = CACHE_DIR / f"enigma-{ENIGMA_VERSION}.jar"

VINEFLOWER_VERSION = "1.11.1"
VINEFLOWER_PATH = CACHE_DIR / f"vineflower-{VINEFLOWER_VERSION}.jar"

VERSIONS_JSON_PATH = CACHE_DIR / "versions.json"


def setup():
    """
    Creates the needed folders and downloads the dependencies.
    """
    # create folders
    OUTPUT_SRC_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # download dependencies
    download_file(
        ENIGMA_PATH,
        f"https://maven.fabricmc.net/cuchaz/enigma-cli/{ENIGMA_VERSION}/enigma-cli-{ENIGMA_VERSION}-all.jar",
    )
    download_file(
        VINEFLOWER_PATH,
        f"https://github.com/Vineflower/vineflower/releases/download/{VINEFLOWER_VERSION}/vineflower-{VINEFLOWER_VERSION}.jar",
    )
    download_file(
        VERSIONS_JSON_PATH,
        "https://piston-meta.mojang.com/mc/game/version_manifest.json",
        force=True,
    )

    # create git repo
    if not (OUTPUT_DIR / ".git").exists():
        os.chdir(OUTPUT_DIR)
        os.system("git init")
        os.chdir("..")


def install_version(version: dict[str, str]):
    """
    Downloads, deobfuscates and pushes a given version to the `SRC_DIR` repo.
    """
    version_id = version["id"]
    logging.info(f"Installing {version_id}...")

    version_json_path = CACHE_DIR / f"{version_id}.json"
    version_jar_path = CACHE_DIR / f"{version_id}.jar"
    mappings_proguard_path = CACHE_DIR / f"{version_id}.mappings"
    mappings_enigma_dir = CACHE_DIR / f"{version_id}.enigma"
    mapped_jar_path = CACHE_DIR / f"{version_id}.mapped.jar"

    # download version json
    download_file(version_json_path, version["url"])
    with version_json_path.open() as f:
        data = json.load(f)

    # download jar and mappings
    download_file(version_jar_path, data["downloads"]["client"]["url"])
    download_file(mappings_proguard_path, data["downloads"]["client_mappings"]["url"])

    # convert mappings
    if not mappings_enigma_dir.exists():
        logging.info("Converting mappings...")
        java.convert_mappings(ENIGMA_PATH, mappings_proguard_path, mappings_enigma_dir)

    # deobfuscate client
    if not mapped_jar_path.exists():
        logging.info("Deobfuscating jar...")
        java.deobfuscate_jar(
            ENIGMA_PATH, version_jar_path, mappings_enigma_dir, mapped_jar_path
        )

    # decompile client
    java.decompile_jar(VINEFLOWER_PATH, mapped_jar_path, OUTPUT_SRC_DIR)

    # save latest installed version
    with (OUTPUT_DIR / "version.json").open("w") as f:
        json.dump(version, f)


def iterate_versions() -> list[dict[str, str]]:
    """
    Detects the current installed version and returns the new updates after that.
    """
    latest_installed = None
    if (latest_path := OUTPUT_DIR / "version.json").exists():
        with latest_path.open() as f:
            data = json.load(f)
            latest_installed = datetime.fromisoformat(data["releaseTime"])

    with VERSIONS_JSON_PATH.open() as f:
        data = json.load(f)
    release = data["latest"]["release"]
    _snapshot = data["latest"]["snapshot"]

    # install from top to latest release, if the releaseTime is newer than the latest version installed
    versions: list[dict] = []
    for version in data["versions"]:
        if not latest_installed or latest_installed < datetime.fromisoformat(
            version["releaseTime"]
        ):
            versions.append(version)

        if version["id"] == release:
            break

    return [*reversed(versions)]


def main():
    setup()

    for version in iterate_versions():
        # clean folder
        shutil.rmtree(OUTPUT_SRC_DIR)
        OUTPUT_SRC_DIR.mkdir(parents=True, exist_ok=True)

        # install version
        install_version(version)

        # commit to git
        os.chdir("mc")
        os.system("git add -A")
        os.system(f"git commit -m {version['id']}")
        os.chdir("..")


def download_file(path: Path, url: str, force=False):
    try:
        if force or not path.exists():
            logging.info(f"Downloading {path}...")
            response = requests.get(url)
            response.raise_for_status()
            with path.open("wb") as f:
                f.write(response.content)
    except requests.RequestException as err:
        logging.error(err)


if __name__ == "__main__":
    main()
