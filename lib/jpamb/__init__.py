from jpamb import jvm
from jpamb.model import Suite


def printinfo(
    name: str,
    version: str,
    tags: list[str],
    for_science: bool,
):
    print(name)
    print(version)
    print(",".join(tags))
    if for_science:
        import platform

        print(platform.platform())

    import sys

    sys.exit(0)


def parse_methodid(mid):
    return jvm.Absolute.decode(mid, jvm.MethodID.decode)
