# v1.8.1
- 🛠 Renamed `lidar-constants-scc` to `scc-lidar-constants`, which better matches the other scc-related commands.

# v1.8.0
- ✨ Add new command `lidar-constants-scc` for downloading the Lidar Constants table as a CSV file from SCC.

# v1.7.2
- 🐜 Fix a small bug in the measurement table parsing that prevented downloads of ELDA files.

# v1.7.1
- 🐜 Fix a bug that caused more than one atmospheric profile to be included in radiosonde files, which in turn caused the "Sounding File Error: Altitude should be in ascending order" error.

# v1.7.0
- ✨ `create-scc`: Add `--atmosphere=` option for selecting which atmosphere to use for molecular calculation. This replaces the old `--no-radiosonde` command.
- 🛠 The default atmosphere is now standard atmosphere instead of collocated radiosonde.

# v1.6.5
- ✨ `search-scc`: Add `--detailed-status` option for fetching the processing status codes from SCC.
- 🐜 Fix a couple of issues related to searching and downloading of products caused by the minor SCC website changes.

# v1.6.4
- ✨ `create-scc`: Add `--system-id-day=` and `--system-id-night=` options to override configuration IDs without making a new location.
- 🐜 Fix %APPDATA% not being expanded in locations path (for real this time).
- 🛠 Rewrite how config paths are handles, this should fix most config-related issues.

# v1.6.3
- 🐜 Fix %APPDATA% not being expanded in locations path.

# v1.6.2
- 🐜 Fix radiosonde files being named `rsYYYYMMDD.nc` instead of `rs_YYYYMMDD.nc`
- 🐜 Fix loading of user locations

# v1.6.1
- ✨ Add `HH:MM:SS` and `YYYY-mm-DD HH:MM:SS` as possible date input formats.

# v1.6.0
- ✨ Added merging of raw files
- ✨ Added the concept of radiosonde providers in order to support different filetypes for sounding
- ✨ Allow full dates in `create-scc`'s `--start-time=` and `--end-time=` options to accomondate for merging multiple days
- ✨ Added new time format for `--start-time=` and `--end-time=`: `XX:MM`. For example `XX:30` will start at the first available half-hour
- 🛠 Print time period contained in each output file when using `create-scc`.
- 🐜 Fix `scc-search` and `scc-search-download` missing the second page of data.
- 🐜 Fix crash on bad `measurement_time` value
- 🐜 Fix `--interval=` not being parsed correctly

# v1.5.0
- ✨ Added `--end-time=` option to `create-scc`, which can be used alongside `--start-time=` to create files for specific
  intervals.
- 🛠 Add more options to the location configs
- 🛠 Changed measurement ID format to use HHMM (hour minutes) for time, instead of start hour and end hour.

# v1.4.0
- ✨ Added new `--start-time=` option to `create-scc` for specifying when the output time should start.
- ✨ You can now set `channel_id`, `background_low`, `background_high` and `input_lr` for custom stations!
- 🐜 Fix crash trying to use `scc-upload` on files without accompaning radiosondes
- 🛠 Print a more helpful message when trying to upload files without being logged in

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