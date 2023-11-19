import json
import logging
import os
import shutil
from datetime import datetime

import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s/%(name)s] %(message)s", datefmt="%H:%M:%S")

# constants

OUTPUT_DIR = "mc"
SRC_DIR = os.path.join(OUTPUT_DIR, "src")
CACHE_DIR = ".cache/"

ENIGMA_PATH = os.path.join(CACHE_DIR, "enigma.jar")
VINEFLOWER_PATH = os.path.join(CACHE_DIR, "vineflower.jar")
VERSIONS_PATH = os.path.join(CACHE_DIR, "versions.json")


def setup():
    """
    Creates the needed folders and downloads the dependencies.
    """
    logging.info("[setup/start]")
    # create folders
    os.makedirs(SRC_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    # download dependencies
    download_file(ENIGMA_PATH, "https://maven.fabricmc.net/cuchaz/enigma-cli/2.3.3/enigma-cli-2.3.3-all.jar")
    download_file(VINEFLOWER_PATH, "https://github.com/Vineflower/vineflower/releases/download/1.9.3/vineflower-1.9.3.jar")
    download_file(VERSIONS_PATH, "https://piston-meta.mojang.com/mc/game/version_manifest.json")

    # create git repo
    if not os.path.exists(os.path.join(OUTPUT_DIR, ".git")):
        os.chdir("mc")
        os.system("git init")
        os.chdir("..")

    logging.info("[setup/done]")


def install_version(version: dict[str, str]):
    logging.info(f"[install/{version['id']}]")

    json_path = os.path.join(CACHE_DIR, f"{version['id']}.json")
    jar_path = os.path.join(CACHE_DIR, f"{version['id']}.jar")
    mappings_path = os.path.join(CACHE_DIR, f"{version['id']}.mappings")
    enigma_mappings_dir = os.path.join(CACHE_DIR, f"{version['id']}.enigma")
    mapped_jar_path = os.path.join(CACHE_DIR, f"{version['id']}.mapped.jar")

    # download version json
    download_file(json_path, version["url"])
    with open(json_path) as f:
        data = json.load(f)

    # download jar and mappings
    download_file(jar_path, data["downloads"]["client"]["url"])
    download_file(mappings_path, data["downloads"]["client_mappings"]["url"])

    # convert mappings
    if not os.path.exists(enigma_mappings_dir):
        logging.info("Converting mappings...")
        os.system(f"java -jar {ENIGMA_PATH} convert-mappings proguard {mappings_path} enigma {enigma_mappings_dir}")

    # map client
    if not os.path.exists(mapped_jar_path):
        logging.info("Deobfuscating jar...")
        os.system(f"java -jar {ENIGMA_PATH} deobfuscate {jar_path} {mapped_jar_path} {enigma_mappings_dir}")

    # decompile client
    args = [
        "java",
        "-jar",
        VINEFLOWER_PATH,
        "-log=error",
        "-vvm=1",  # check validity
        "-ump=0",  # don't use parameter names as given by MethodParameters attribute
        "-udv=0",  # ignore LVT names for local and params
        "-jvn=1",  # JAD-style names for local variables
        "-jpr=1",  # JAD-style names for parameters
        "-vac=1",  # Verify that anonymous classes are local
        mapped_jar_path,
        SRC_DIR,
    ]
    os.system(" ".join(args))

    # save latest installed version
    with open(os.path.join(OUTPUT_DIR, "version.json"), "w") as f:
        json.dump(version, f)


def iterate_versions() -> list[dict[str, str]]:
    latest_installed = None
    if os.path.exists(latest_path := os.path.join(OUTPUT_DIR, "version.json")):
        with open(latest_path) as f:
            data = json.load(f)
            latest_installed = datetime.fromisoformat(data["releaseTime"])

    with open(VERSIONS_PATH) as f:
        data = json.load(f)
    release = data["latest"]["release"]
    snapshot = data["latest"]["snapshot"]

    # install from top to latest release, if the releaseTime is newer than the latest version installed
    versions: list[dict] = []
    for version in data["versions"]:
        if not latest_installed or latest_installed < datetime.fromisoformat(version["releaseTime"]):
            versions.append(version)

        if version["id"] == release:
            break

    return [*reversed(versions)]


def main():
    setup()

    for version in iterate_versions():
        # clean folder
        shutil.rmtree(SRC_DIR)
        os.makedirs(SRC_DIR, exist_ok=True)

        # install version
        install_version(version)

        # commit to git
        os.chdir("mc")
        os.system("git add -A")
        os.system(f"git commit -m {version['id']}")
        os.chdir("..")


def download_file(path: str, url: str):
    try:
        if not os.path.exists(path):
            logging.info(f"Downloading {path}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(path, "wb") as f:
                f.write(response.content)
    except requests.RequestException as err:
        logging.error(err)


if __name__ == "__main__":
    main()
