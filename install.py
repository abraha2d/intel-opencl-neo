#!/usr/bin/env python3

"""
An installer for the Intel(R) Graphics Compute Runtime for OpenCL(TM).
Installs the requested version from the configured repository.
"""

__version__ = "0.3.0"

import cssselect
import lxml.html
import os
import requests
import subprocess
import sys
import tempfile
import tqdm

# ---------------
# Configuration
#

GH_REPO_RUNTIME = "intel/compute-runtime"
GH_REPO_COMPILER = "intel/intel-graphics-compiler"

CHUNK_SIZE = 8192

DEBUG = True

# ------------------------
# Advanced Configuration
#

RELEASE_URL = "https://github.com/{}/releases/{}"

ASSET_SELECTOR = "li.Box-row > a"


# -----------
# Utilities
#

class C:
    BLK = 0
    RED = 1
    GRN = 2
    YEL = 3
    BLU = 4
    MAG = 5
    CYA = 6
    WHT = 7


def c(fg=None, bg=None, fg_bright=False, bg_bright=False):
    parts = []
    if fg is not None:
        parts.append(str(fg + (90 if fg_bright else 30)))
    if bg is not None:
        parts.append(str(bg + (100 if bg_bright else 40)))
    return f"\x1B[{';'.join(parts)}m"


OK = (' OK ', c(C.GRN), True)
EMPTY = ('    ', c(C.WHT), False)
INFO = ('INFO', c(C.CYA), False)
DBUG = ('DBUG', c(C.MAG), False)
WARN = ('WARN', c(C.YEL), False)
FAIL = ('FAIL', c(C.RED), True)


def print_(p_type, *args, **kwargs):
    if p_type == DBUG and not DEBUG:
        return
    prefix = f"\x1B[G{p_type[1]}[{p_type[0]}]{c()}"
    if kwargs.pop('replace', p_type[2]):
        prefix = "\x1B[A" + prefix
        if args:
            args = args + ("\x1B[K",)
    kwargs.pop('sep', None)
    print(prefix, *args, **kwargs, sep=' ')


def handle_connection_error(e):
    print_(FAIL)
    try:
        e = e.args[0]
        e = e.reason
        e = e.args[0]
        e = e.split(": ")[-1]
    finally:
        print_(INFO, f"Encountered {e}.")
    exit(1)


def handle_encoding_error(e):
    print_(FAIL)
    try:
        e = e.args[-1]
        e = e.args[-1]
        e = str(e)
    finally:
        print_(INFO, f"Encountered {e}.")
    exit(1)


# -----------
# Functions
#

def get_release_page(repo, version="latest"):
    """
  Retrieves the HTML page corresponding to the requested version.
  """
    try:
        if version == "latest":
            print_(EMPTY, "Getting latest release details...")
            r = requests.get(RELEASE_URL.format(repo, version))
        else:
            print_(EMPTY, f"Getting details for release {version}...")
            r = requests.get(RELEASE_URL.format(repo, f"tag/{version}"))
    except requests.exceptions.RequestException as e:
        handle_connection_error(e)
        return

    if r:
        print_(OK)
        if version == "latest":
            latest_version = r.url.split('/')[-1]
            print_(INFO, f"Latest release: {latest_version}")
    else:
        print_(FAIL)
        if r.status_code == 404:
            print_(INFO, "Release not found.")
        else:
            print_(INFO, f"Status code: {r.status_code}")
        exit(1)

    return r.text


def download_asset(asset, directory):
    """
  Downloads the asset from the specified URL into the specified directory.
  """
    asset_basename = os.path.basename(asset)
    print_(EMPTY, f"Downloading asset: {asset_basename}")
    try:
        r = requests.get(asset, stream=True)
        if not r:
            print_(FAIL)
            if r.status_code == 404:
                print_(INFO, "Asset not found.")
            else:
                print_(INFO, f"Status code: {r.status_code}")
            exit(1)
        with open(os.path.join(directory, asset_basename), 'wb') as f:
            with tqdm.tqdm(
                    total=int(r.headers['Content-Length']),
                    leave=False, miniters=1,
                    unit='B', unit_scale=True
            ) as pbar:
                try:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            f.flush()
                            pbar.update(len(chunk))
                except KeyboardInterrupt as e:
                    print("\x1B[A\x1B[2K", end='')
                    raise e
    except requests.exceptions.ChunkedEncodingError as e:
        handle_encoding_error(e)
    except requests.exceptions.ConnectionError as e:
        handle_connection_error(e)
        return

    print_(OK)


def download_assets(page, directory=None):
    """
  Downloads assets from the given page into a temporary directory.
  """
    print_(EMPTY, "Compiling list of assets to download...")
    try:
        expression = cssselect.HTMLTranslator().css_to_xpath(ASSET_SELECTOR)
    except cssselect.SelectorError:
        print_(FAIL)
        print_(INFO, "Invalid ASSET_SELECTOR configured.")
        exit(1)
        return
    asset_list = [
        "https://github.com" + e.get('href')
        for e in lxml.html.fromstring(page).xpath(expression)
        if "Source code" not in e[0].text
    ]
    print_(OK)

    tmp_dir = directory or tempfile.mkdtemp(prefix='intel-opencl-neo-')
    if directory is None:
        print_(DBUG, f"Temporary directory: {tmp_dir}")

    for asset in asset_list:
        download_asset(asset, tmp_dir)

    return tmp_dir


def run_command(cmd, directory):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        cwd=directory,
        universal_newlines=True,
        bufsize=1,
    )

    i = 0

    try:
        for line in iter(process.stdout.readline, ''):
            i += 1
            print(line, end='')
            sys.stdout.flush()
        process.wait()
        failure = process.returncode
    except KeyboardInterrupt:
        print("\x1B[A" * i, end='')
        print_(FAIL)
        print("\x1B[B" * i, end='')
        print_(INFO, "Interrupted.")
        exit(2)
        return

    print("\x1B[A" * i, end='')
    print_(FAIL if failure else OK)
    print("\x1B[B" * i, end='')
    if failure:
        exit(1)


def verify_assets(directory):
    """
  Verifies integrity of assets in the specified directory.
  """
    print_(EMPTY, "Verifying assets...")
    run_command("sha256sum -c *.sum", directory)


def install_assets(directory):
    """
  Installs assets from the specified directory.
  """
    print_(EMPTY, "Installing assets...")
    run_command("sudo dpkg -iRB .", directory)


def print_usage():
    """
  Prints the usage of the program.
  """

    basename = os.path.basename(sys.argv[0])

    print(f"""{__doc__}
Configured repositories:
- {GH_REPO_RUNTIME}
- {GH_REPO_COMPILER}

Usage:
  {basename}
  {basename} <runtime version> <compiler version>
  {basename} -h | --help
  {basename} --version

If <runtime version> and <compiler version> are not specified, the latest versions will be installed.

Options:
  -h --help     Show this screen.
  -v --version  Show version.
""")


# ------------
# Main Logic
#

def main():
    runtime_page = get_release_page(GH_REPO_RUNTIME, sys.argv[1] if len(sys.argv) > 2 else "latest")
    directory = download_assets(runtime_page)

    compiler_page = get_release_page(GH_REPO_COMPILER, sys.argv[2] if len(sys.argv) > 2 else "latest")
    download_assets(compiler_page, directory)

    verify_assets(directory)
    install_assets(directory)

    print_(OK, "All done.", replace=False)


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print_usage()
        exit(0)

    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{__version__}")
        exit(0)

    for arg in sys.argv:
        if arg[0] == "-":
            print_(FAIL, f"Unknown option \"{arg}\"", replace=False)
            print_usage()
            exit(1)

    if 1 < len(sys.argv) < 3:
        print_(FAIL, "Not enough arguments.", replace=False)
        print_usage()
        exit(1)

    if len(sys.argv) > 3:
        print_(FAIL, "Too many arguments.", replace=False)
        print_usage()
        exit(1)

    try:
        main()
    except KeyboardInterrupt:
        print_(FAIL)
        print_(INFO, "Interrupted.")
        exit(2)
