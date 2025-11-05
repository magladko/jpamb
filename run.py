#!/usr/bin/env python3

import sys
import os
import shutil

if len(sys.argv) >= 3 and sys.argv[1] == "-D":
    docker = sys.argv[2]
    if docker is not None:
        if docker == "-":
            docker = "latest"
        if ":" not in docker:
            docker = f"ghcr.io/kalhauge/jpamb:{docker}"

        dockerbin = shutil.which("podman") or shutil.which("docker")
        if not dockerbin:
            print("Could not find docker on path.")
            sys.exit(-1)

        path = os.getcwd()

        cmd = [
            dockerbin,
            "run",
            "--rm",
            "-v",
            f"{path}:/workspace",
            docker,
            "python3",
            "-m",
            "jpamb.cli",
        ] + sys.argv[3:]

        os.execv(dockerbin, cmd)

if (uvbin := shutil.which("uv")) is not None:
    cmd = [uvbin, "run", "python", "-m", "jpamb.cli"] + sys.argv[1:]
    os.execv(uvbin, cmd)


if (pythonbin := shutil.which("python3") or shutil.which("python")) is not None:
    cmd = [pythonbin, "-m", "jpamb.cli"] + sys.argv[1:]
    os.execv(pythonbin, cmd)
