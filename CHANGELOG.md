# 1.16.2

- 🐜 Fixed wrong paths being shown in `locations-show` command.

# 1.16.0

- 🛠 `create-scc`: Allow `--interval` to be used alongside `--start-time` and `--end-time`.
- 🐜 `create-scc`: Fix time calculation for `Raw_Data_Start_Time`, fixes issue with time non-continuities with files that contained midnight.
- 🐜 Removed 30s of extra length at the end of each file.

# 1.15.0

- 🛠 Mark as compatible with Python 3.12
- 🛠 Make 3.9 the minimum Python version
- 🐜 Fix package version login
- 🐜 Add crash w/ explaination when qc-eldec logic cannot handle a calibration file

# 1.14.5

- 🐜 Fix a crash when a station's location was near to the poles and subject to long nights or days.

# 1.14.4

- 🐜 Fix an issue that produced empty calibration files when depol_cal_angle was not 0 (Thanks @ulysses78!)

# 1.14.3

- 🛠 Change sunset time for Antikythera to 16:00

# 1.14.2

- 🐜 Small compatibility fix with SCC API
- 🐜 Mark as compatible with Python 3.11

# 1.14.1

- ✨ Add support for the new `channel_string_IDs` variable.

# 1.14.0

- ✨ Add ability to adjust sunset and sunrise times, used for determining the correct configuration ID.

# 1.13.2

- 🐜 Fix type annotation issue breaking compatibility with Python <3.10

# 1.13.1

- ✨ Add CVO to default locations

# 1.13.0

- ✨ Add support for 1064nm depolarization channels
- ✨ Make all depolarization channels optional. When the corresponding options are missing from the configuration file, that channel is silently ignored.

# 1.12.1

- 🐜 When the two depol. calibration cycles are not of same length, attempt to handle it by clipping the largest one so it matches the smaller one.

# 1.12.0

- ✨⚠️ Add new `depol_calibration_zero_state` setting to locations for configuring which value `depol_cal_angle` takes when no calibration takes place.
- 🛠 Change how depolarization calibration files are generated, files should now be correct for consumption by SCC. See documentation for detailed explanation.
- 🐜 Fix some error handling when uploading malformed SCC files.

# 1.11.0

- 🛠 Data during depolarization calibration are now removed from the SCC files. This replaces the old behaviour that set this period to NaN.
- 🐜 Fix `scc-download`, `scc-search` and `scc-search-download` not working due to an issue in creating `Measurement()` internally. Fixes regression introduced in 1.10.0.

# 1.10.0

- ✨ Add new `scc-auto-upload-calibration` command which uploads a depol calibration file, waits for results and downloads the ELDEC file. If the eldec file does not pass the QC check (see. `qc-eldec`), the calibration file is deleted from SCC.
- 🐜 Fix not being able to upload a single file using `scc-upload`
- 🐜 Fix calibration files having NaN values in Raw_Lidar_Data
- 🐜 Show correct error message when given directory has no netCDF files `scc-upload`

# 1.9.0

- ✨ Add new `qc-eldec` command for performing quality checks on calibration, based on the ELDEC file.
- ✨ Add new `qc-eldec-clean-history` command for clearing the history of `qc-eldec`.
- ✨ Add calibration file (`calibration_*.nc`) uploading. Added calibration system IDs to locations.
- ✨ Calibration files are generated based on `depol_cal_angle` being non-zero and not on fixed times.
- 🛠⚠️ Renamed the `NOAReACT_Configuration_ID` attribute that the application put in SCC files to `X_PollyXTPipelines_Configuration_ID`. SCC files created by older versions cannot be uploaded.
- 🛠 Updated dependencies
- 🐜 Fix data (`raw_signal`) not being set to NaN during calibration times (based on `depol_cal_angle`).

# v1.8.3

- ✨ `create-scc`: Generate calibration files for both 532nm and 355nm

# v1.8.2

- 🛠 Pad `end_time` of created SCC files a bit to avoid files ending in :29 instead of :30 (and :59 instead of :00).

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
