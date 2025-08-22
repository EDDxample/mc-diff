import subprocess
from pathlib import Path

JAVA_PATH = Path("java")


def convert_mappings(enigma_jar: Path, input_mappings: Path, output_dir: Path):
    cmd = [
        JAVA_PATH,
        "-jar",
        enigma_jar,
        "convert-mappings",
        "proguard",
        input_mappings,
        "enigma",
        output_dir,
    ]
    subprocess.run(cmd, check=True, shell=True)


def deobfuscate_jar(
    enigma_jar: Path, input_jar: Path, enigma_mappings: Path, output_path: Path
):
    cmd = [
        JAVA_PATH,
        "-jar",
        enigma_jar,
        "deobfuscate",
        input_jar,
        output_path,
        enigma_mappings,
    ]
    subprocess.run(cmd, check=True, shell=True)


def decompile_jar(vineflower_jar: Path, mapped_jar: Path, output_dir: Path):
    cmd = [
        JAVA_PATH,
        "-jar",
        vineflower_jar,
        "-log=error",
        "-vvm=1",  # check validity
        "-ump=0",  # don't use parameter names as given by MethodParameters attribute
        "-udv=0",  # ignore LVT names for local and params
        "-jvn=1",  # JAD-style names for local variables
        "-jpr=1",  # JAD-style names for parameters
        "-vac=1",  # verify that anonymous classes are local
        mapped_jar,
        output_dir,
    ]
    subprocess.run(cmd, check=True, shell=True)
