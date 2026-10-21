"""Single-threaded limit setup before exec; no preexec_fn in the parent."""

import os
import resource
import sys


def main():
    maximum = int(sys.argv[1])
    if not 0 < maximum <= 32 * 1024**2 or len(sys.argv) < 3:
        raise ValueError("invalid_limited_child")
    resource.setrlimit(resource.RLIMIT_FSIZE, (maximum, maximum))
    os.execv(sys.argv[2], sys.argv[2:])


if __name__ == "__main__":
    main()
