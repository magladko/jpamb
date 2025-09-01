from jpamb import jvm
from jpamb.model import Suite


def getmethodid(
    name: str,
    version: str,
    group: str,
    tags: list[str],
    for_science: bool,
):
    import sys

    mid = sys.argv[1]
    if mid == "info":
        printinfo(name, version, group, tags, for_science)

    return parse_methodid(mid)


def printinfo(
    name: str,
    version: str,
    group: str,
    tags: list[str],
    for_science: bool,
):
    print(name)
    print(version)
    print(group)
    print(",".join(tags))
    if for_science:
        import platform

        print(platform.platform())

    import sys

    sys.exit(0)


def parse_methodid(mid):
    return jvm.Absolute.decode(mid, jvm.MethodID.decode)
