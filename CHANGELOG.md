# Changelog


## v0.3.0 (2021-11-20)

`intel-opencl` has been replaced by `intel-opencl-icd` since ICR 21.42.21270.
After updating past this version of ICR, you may need to run `sudo apt -f install` to fix conflicts.

Also, GitHub's release page format has changed slightly.

### Changes
- Updated installer to allow for de-configuration of `intel-opencl`.
- Updated scraper to parse GitHub's new release page format.
- Added `bootstrap.sh` to set up a virtual environment with the necessary dependencies.
- Added this CHANGELOG file.


## v0.2.1 (2021-06-19)

### Changes
- Fixed bugs in argument handling.


## v0.2.0 (2020-12-17)

Intel Compute Runtime and Intel Graphics Compiler are released in separate repos since ICR 20.37.17906 / IGC 1.0.4944.

### Changes
- Updated installer to download assets from both repositories.
- Added dependencies to the README.


## v0.1.0 (2019-12-15)

Initial release