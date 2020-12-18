# v1.3.0
- ✨ Added support for custom locations! New commands `locations-show` and `locations-path` to accomodate new system.
- ✨ Added new `login` command for... logging in.
- 🚨 Merged `scc-create` and `scc-create-batch` into one command that does both
- 🚨 Moved config from `~/.config/pollyxt_pipelines.ini` to `~/.config/pollyxt_pipelines/pollyxt_pipelines.ini` in order
  to accomodate the new `locations.ini` file. No changes on Windows.
- 🛠 Correctly set `Molecular_Calc` variable when using `-no-radiosonde` option.

# v1.2.0
- ✨ Add `scc-delete` command for deleting measurements from the SCC database
- ✨ Add `scc-rerun` command for requesting re-processing of measurements
- 🐜 Fix crash when using `scc-download` with `--id` option

# v1.1.0
- Add `scc-search` and `scc-search-download` commands
- Create documentation page using sphinx
- Better error handling due to new internal SCC API

# v1.0.1
- Use a config variable instead of environmental for WRF profiles path

# v1.0.0
- First release!