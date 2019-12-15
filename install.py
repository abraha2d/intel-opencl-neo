#!/usr/bin/env python3

"""
An installer for the Intel(R) Graphics Compute Runtime for OpenCL(TM).
Installs the requested version from the configured repository.
"""

VERSION = "0.1.0"


import cssselect
import curses
import lxml.html
import os
import requests
import subprocess
import sys
import tempfile
import tqdm


#---------------
# Configuration
#

GITHUB_REPO = "intel/compute-runtime"

CHUNK_SIZE = 8192

DEBUG = True


#------------------------
# Advanced Configuration
#

RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/" + "{}"

ASSET_SELECTOR = ".Box > div > .d-flex > a"


#-----------
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
  l = []
  if fg is not None: l.append(str(fg + (90 if fg_bright else 30)))
  if bg is not None: l.append(str(bg + (100 if bg_bright else 40)))
  return f"\x1B[{';'.join(l)}m"

OK =    (' OK ', c(C.GRN), True)
EMPTY = ('    ', c(C.WHT), False)
INFO =  ('INFO', c(C.CYA), False)
DBUG =  ('DBUG', c(C.MAG), False)
WARN =  ('WARN', c(C.YEL), False)
FAIL =  ('FAIL', c(C.RED), True)

def print_(type, *args, **kwargs):
  if type == DBUG and not DEBUG:
    return
  prefix = f"\x1B[G{type[1]}[{type[0]}]{c()}"
  if kwargs.pop('replace', type[2]):
    prefix = "\x1B[A" + prefix
    if args:
      args = args + ("\x1B[K",)
  kwargs.pop('sep', None)
  print(prefix, *args, **kwargs, sep=' ')


#-----------
# Functions
#

def get_release_page(version="latest"):
  """
  Retrieves the HTML page corresponding to the requested version.
  """
  try:
    if version == "latest":
      print_(EMPTY, "Getting latest release details...")
      r = requests.get(RELEASE_URL.format(version))
    else:
      print_(EMPTY, f"Getting details for release {version}...")
      r = requests.get(RELEASE_URL.format(f"tag/{version}"))
  except requests.exceptions.RequestException as e:
    print_(FAIL)
    try:
      e = e.args[0]
      e = e.reason
      e = e.args[0]
      e = e.split(": ")[-1]
    finally:
      print_(INFO, f"Encountered {e}.")
    exit(1)

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


def download_asset(asset, dir):
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
    with open(os.path.join(dir, asset_basename), 'wb') as f:
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
    print_(FAIL)
    try:
      e = e.args[-1]
      e = e.args[-1]
      e = str(e)
    finally:
      print_(INFO, f"Encountered {e}.")
    exit(1)
  except requests.exceptions.ConnectionError as e:
    print_(FAIL)
    try:
      e = e.args[0]
      e = e.reason
      e = e.args[0]
      e = e.split(": ")[-1]
    finally:
      print_(INFO, f"Encountered {e}.")
    exit(1)

  print_(OK)


def download_assets(page):
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
  asset_list = [
    "https://github.com" + e.get('href')
    for e in lxml.html.fromstring(page).xpath(expression)]
  print_(OK)

  tmp_dir = tempfile.mkdtemp(prefix='intel-opencl-neo-')
  print_(DBUG, f"Temporary directory: {tmp_dir}")

  for asset in asset_list:
    download_asset(asset, tmp_dir)

  return tmp_dir


def run_command(cmd, dir):
  process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    shell=True,
    cwd=dir,
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
  except KeyboardInterrupt as e:
    print("\x1B[A"*i, end='')
    print_(FAIL)
    print("\x1B[B"*i, end='')
    print_(INFO, "Interrupted.")
    exit(2)

  print("\x1B[A"*i, end='')
  print_(FAIL if failure else OK)
  print("\x1B[B"*i, end='')
  if failure:
    exit(1)


def verify_assets(dir):
  """
  Verifies integrity of assets in the specified directory.
  """
  print_(EMPTY, "Verifying assets...")
  run_command("sha256sum -c *.sum", dir)


def install_assets(dir):
  """
  Installs assets from the specified directory.
  """
  print_(EMPTY, "Installing assets...")
  run_command("sudo dpkg -i *.deb", dir)


def print_usage():
  """
  Prints the usage of the program.
  """

  basename = os.path.basename(sys.argv[0])

  print(f"""{__doc__}
Configured repository: {GITHUB_REPO}

Usage:
  {basename} [<release>]
  {basename} -h | --help
  {basename} --version

If <release> is not specified, the latest release will be installed.

Options:
  -h --help     Show this screen.
  -v --version  Show version.
""")


#------------
# Main Logic
#

def main():
  page = get_release_page(sys.argv[1] if len(sys.argv) > 1 else "latest")
  dir = download_assets(page)
  verify_assets(dir)
  install_assets(dir)
  print_(OK, "All done.", replace=False)


if __name__ == "__main__":
  if "-h" in sys.argv or "--help" in sys.argv:
    print_usage()
    exit(0)

  if len(sys.argv) > 2:
    print_(FAIL, "Too many arguments.", replace=False)
    print_usage()
    exit(1)

  if "-v" in sys.argv or "--version" in sys.argv:
    print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
    exit(0)

  if len(sys.argv) > 1 and sys.argv[1][0] == "-":
    print_(FAIL, f"Unknown option \"{sys.argv[1]}\"", replace=False)
    print_usage()
    exit(1)

  try:
    main()
  except KeyboardInterrupt:
    print_(FAIL)
    print_(INFO, "Interrupted.")
    exit(2)
