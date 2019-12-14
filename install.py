#!/usr/bin/env python3

VERSION = "0.1.0"

import curses
from os.path import basename
import requests
import sys


RELEASE_URL = "https://github.com/intel/compute-runtime/releases/{}"


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

def print_(*args, **kwargs):
  print(f"\x1B[G{c(C.WHT)}[    ]{c()}", *args, **kwargs, sep=' ')

def print_blank(*args, **kwargs):
  print(f"\x1B[G      ", *args, **kwargs, sep=' ')

def print_ok(*args, **kwargs):
  if args:
    args = args + ("\x1B[K",)
  print(f"\x1B[A\x1B[G{c(C.GRN)}[ OK ]{c()}", *args, **kwargs, sep=' ')

def print_fail(*args, **kwargs):
  if args:
    args = args + ("\x1B[K",)
  print(f"\x1B[A\x1B[G{c(C.RED)}[FAIL]{c()}", *args, **kwargs, sep=' ')


def get_release_page(version="latest"):
  try:
    if version == "latest":
      print_("Getting details of latest release...")
      r = requests.get(RELEASE_URL.format(version))
    else:
      print_(f"Getting details of release {version}...")
      r = requests.get(RELEASE_URL.format(f"tag/{version}"))
  except requests.exceptions.ConnectionError as e:
    print_fail()
    try:
      e = e.args[0]
      e = e.reason
      e = e.args[0]
      e = e.split(": ")[-1]
    finally:
      print_blank(f"{e}")
    exit(1)

  if r:
    print_ok()
    if version == "latest":
      latest_version = r.url.split('/')[-1]
      print_blank(f"Latest release: {latest_version}")
  else:
    print_fail()
    if r.status_code == 404:
      print_blank("Release not found.")
    else:
      print_blank(f"Status code: {r.status_code}")
    exit(1)

  return r.text


def main():
  p = get_release_page(sys.argv[1] if len(sys.argv) > 1 else "latest")


def print_usage():
  print(f"""
An installer for the Intel(R) Graphics Compute Runtime for OpenCL(TM).

Usage:
  {basename(sys.argv[0])} [<release>]
  {basename(sys.argv[0])} -h | --help
  {basename(sys.argv[0])} --version

If <release> is not specified, the latest release will be installed.

Options:
  -h --help     Show this screen.
  -v --version  Show version.
""")

if __name__ == "__main__":
  if "-h" in sys.argv or "--help" in sys.argv:
    print_usage()
    exit(0)

  if len(sys.argv) > 2:
    print_()
    print_fail("Too many arguments!")
    print_usage()
    exit(1)

  if "-v" in sys.argv or "--version" in sys.argv:
    print(f"{basename(sys.argv[0])} v{VERSION}")
    exit(0)

  if len(sys.argv) > 1 and sys.argv[1][0] == "-":
    print_()
    print_fail(f"Unknown option \"{sys.argv[1]}\"")
    print_usage()
    exit(1)

  main()
