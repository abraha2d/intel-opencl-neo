#!/usr/bin/env python3

"""
An installer for the Intel(R) Graphics Compute Runtime for OpenCL(TM).
Installs the requested version from https://github.com/intel/compute-runtime.
"""

VERSION = "0.1.0"


import curses
from os.path import basename
import requests
import sys


#---------------
# Configuration
#

RELEASE_URL = "https://github.com/intel/compute-runtime/releases/{}"


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
WARN =  ('WARN', c(C.YEL), False)
FAIL =  ('FAIL', c(C.RED), True)

def print_(type, *args, **kwargs):
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
  except requests.exceptions.ConnectionError as e:
    print_(FAIL)
    try:
      e = e.args[0]
      e = e.reason
      e = e.args[0]
      e = e.split(": ")[-1]
    finally:
      print_(INFO, f"Encountered {e}")
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


def print_usage():
  """
  Prints the usage of the program.
  """

  print(f"""{__doc__}

Usage:
  {basename(sys.argv[0])} [<release>]
  {basename(sys.argv[0])} -h | --help
  {basename(sys.argv[0])} --version

If <release> is not specified, the latest release will be installed.

Options:
  -h --help     Show this screen.
  -v --version  Show version.
""")


#------------
# Main Logic
#

def main():
  p = get_release_page(sys.argv[1] if len(sys.argv) > 1 else "latest")


if __name__ == "__main__":
  if "-h" in sys.argv or "--help" in sys.argv:
    print_usage()
    exit(0)

  if len(sys.argv) > 2:
    print_(FAIL, "Too many arguments!", replace=False)
    print_usage()
    exit(1)

  if "-v" in sys.argv or "--version" in sys.argv:
    print(f"{basename(sys.argv[0])} v{VERSION}")
    exit(0)

  if len(sys.argv) > 1 and sys.argv[1][0] == "-":
    print_(FAIL, f"Unknown option \"{sys.argv[1]}\"", replace=False)
    print_usage()
    exit(1)

  main()
