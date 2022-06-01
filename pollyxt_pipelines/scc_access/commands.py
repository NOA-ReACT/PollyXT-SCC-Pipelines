import logging
import datetime
import getpass
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import time

from cleo import Command
import pandas as pd
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, track
from netCDF4 import Dataset

from pollyxt_pipelines.console import console
from pollyxt_pipelines import locations
from pollyxt_pipelines.scc_access import scc_session, SCC, SCC_Credentials, exceptions
from pollyxt_pipelines.config import Config, config_paths, print_login_error
from pollyxt_pipelines.utils import option_to_bool
from pollyxt_pipelines.qc_eldec import qc_eldec_file
from pollyxt_pipelines.scc_access.types import ProductStatus


class Login(Command):
    """
    Provide the necessary credentials for authenticating with SCC

    login
    """

    def handle(self):
        # Print warning!
        path = config_paths()[-1]
        warning_md = (
            "Your credentials will be stored as **PLAIN-TEXT** in the following file:\n"
        )
        warning_md += f"\n* {path}\n"
        warning_md += "\nPlease make sure you understand the security implications of this and keep the config files safe!"
        warning_md = Markdown(warning_md)

        console.print(Panel(warning_md))

        # Ask for the credentials
        console.print(
            "Please enter the HTTP authentication credentials (this is the first login popup when you access the website):"
        )
        console.print(
            "[warn]The password won't be visible while you are typing![/warn]"
        )
        http_username = input("Username: ")
        http_password = getpass.getpass("Password: ")

        console.print("Please enter your account login:")
        auth_username = input("Username: ")
        auth_password = getpass.getpass("Password: ")

        # Store in config
        config = Config()
        config["http"]["username"] = http_username
        config["http"]["password"] = http_password
        config["auth"]["username"] = auth_username
        config["auth"]["password"] = auth_password
        credentials = SCC_Credentials(config)

        # Attempt to login
        try:
            scc = SCC(credentials)
            scc.login()
            scc.logout()
        except exceptions.WrongCredentialsException:
            console.print("[error]Could not login: Wrong credentials![/error]")
            return 1
        except exceptions.PageNotAccessible:
            console.print("[error]Could not login: Page not accessible[/error]")
            console.print("This is probably caused by wrong HTTP credentials!")
            return 1
        except:
            console.print("[error]Could not login (unknown reason!)[/error]")
            return 1

        console.print("[info]Logged in successfully! Credentials saved![/info]")
        config.write()


class UploadFiles(Command):
    """
    Batch upload files to SCC

    scc-upload
        {path : Path to SCC files. If it is a directory, all netCDF files inside will be uploaded.}
        {--no-calibration : If uploading a directory, do not upload calibration files.}
        {list? : Optionally, store the uploaded file IDs in order to later download the products using scc-download}
    """

    def handle(self):
        # Parse arguments
        path = Path(self.argument("path"))
        if path.is_dir():
            files = path.glob("*.nc")
            files = filter(lambda x: not x.name.startswith("rs_"), files)
            if self.option("no-calibration"):
                files = filter(lambda x: not x.name.startswith("calibration_"), files)
        else:
            files = [path]

        files = list(files)
        if len(files) == 0:
            console.print("[error]No files found in given directory[/error]")
            return 1

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Upload files
        successful_files = []
        successful_ids = []
        with scc_session(credentials) as scc:
            for file in track(files, description="Uploading files...", console=console):
                # Read file to find radiosondes
                nc = Dataset(file, "r")
                try:
                    radiosonde_path = file.parent / nc.Sounding_File_Name
                except AttributeError:
                    radiosonde_path = None
                dataset_id = nc.Measurement_ID
                configuration_id = nc.X_PollyXTPipelines_Configuration_ID
                nc.close()

                if radiosonde_path is not None and not radiosonde_path.exists():
                    console.print(
                        f"[error]Cannot find radiosonde file[/error] {radiosonde_path} [error] for measurement [/error] {file} [error]. Skipping file.[/error]"
                    )
                    continue

                # Upload file to SCC
                try:
                    scc.upload_file(file, configuration_id, rs_filename=radiosonde_path)
                    successful_files.append(file)
                    successful_ids.append(dataset_id)
                except exceptions.SCCError as ex:
                    console.print(
                        f"[error]Error while uploading[/error] {file}[error]:[/error] {str(ex)}"
                    )
                except Exception:
                    console.print(
                        f"[error]Unknown error while uploading[/error] {file}"
                    )
                    console.print_exception()

        successful_count = len(successful_ids)
        if successful_count == 0:
            console.print("[warn]No files were uploaded successfully![/warn]")
            return 0
        else:
            console.print(
                f"[info]Successfully uploaded[/info] {successful_count} [info]files.[/info]"
            )

        # Write list file if requested
        list_file = self.argument("list")
        if list_file is not None:
            list_file = Path(list_file)

            df = pd.DataFrame()
            df["Filename"] = successful_files
            df["id"] = successful_ids
            df["Products_Downloaded"] = False

            df.to_csv(list_file, index=False)
            self.line(f"<comment>Wrote IDs to </comment>{list_file}")


class DownloadFiles(Command):
    """
    Batch download files from SCC

    scc-download
        {output-directory : Where to store the processing products}
        {list? : Path to list file generated by `scc-upload`. Checks all files and downloads all available products}
        {--id=* : Optionally, instead of a list file, you can write IDs manually.}
    """

    def handle(self):
        # Check output directory
        output_directory = Path(self.argument("output-directory"))
        output_directory.mkdir(parents=True, exist_ok=True)

        # Check if list or IDs are defined
        id_frame = None
        id_list_file = self.argument("list")
        if id_list_file is None:
            ids = self.option("id")
            if ids is None or len(ids) == 0:
                self.line_error(
                    "Either a list file or some measurement IDs must be provided!"
                )
                return 1
        else:
            id_frame = pd.read_csv(id_list_file, index_col="id")
            ids = id_frame.index

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Download files for each ID
        with scc_session(credentials) as scc:
            for id in track(ids, description="Downloading products", console=console):
                # Check if processing is done
                measurement = scc.get_measurement(id)
                if measurement.is_processing:
                    console.print(
                        f"[warn]File[/warn] {id} [warn]is still processing.[/warn]"
                    )
                    continue

                for file in scc.download_products(id, output_directory):
                    console.print(f"[info]Downloaded[/info] {file}")
                if id_frame is not None:
                    id_frame.loc[id, "Products_Downloaded"] = True


class DeleteSCC(Command):
    """
    Delete measurements from SCC

    scc-delete
        {id* : The measurement IDs to delete from SCC}
    """

    help = """
    This command will *DELETE* measurements from SCC WITHOUT CONFIRMATION! Please be extra
    careful when using it.

    Example usage:
        pollyxt_pipelines scc-delete 20201124aky0001 20201124aky0102
    """

    def handle(self):
        ids = self.argument("id")

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Login to SCC
        successes = []
        failures = []
        with scc_session(credentials) as scc:
            with Progress(console=console) as progress:
                task = progress.add_task("Deleting measurements...", total=len(ids))

                for id in ids:
                    try:
                        scc.delete_measurement(id)
                        console.print(f"[info]Deleted[/info] {id}")
                        successes.append(id)
                    except Exception as ex:
                        console.print(
                            f"-> [error]Could not delete:[/error] {id}", style="bold"
                        )
                        console.print(f"[error]{type(ex).__name__}:[/error] {str(ex)}")
                        failures.append(id)

                    progress.advance(task)

        # Print a summary
        summary = "---\n"
        if len(successes) > 0:
            summary += "**Successfully deleted:**\n"
            for id in successes:
                summary += f"* {id}\n"
        if len(failures) > 0:
            summary += "\n**Not deleted due to failure:**\n"
            for id in failures:
                summary += f"* {id}\n"

        console.print(Markdown(summary))


class RerunSCC(Command):
    """
    Asks SCC to re-run processing for a set of measurements

    scc-rerun
        {id* : The measurement IDs to re-run on SCC}
    """

    def handle(self):
        ids = self.argument("id")

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Login to SCC
        successes = []
        failures = []
        with scc_session(credentials) as scc:
            with Progress(console=console) as progress:
                task = progress.add_task("Asking for re-runs...", total=len(ids))

                for id in ids:
                    try:
                        scc.rerun_processing(id)
                        console.print(f"[info]Re-running[/info] {id}")
                        successes.append(id)
                    except Exception as ex:
                        console.print(
                            f"-> [error]Could not make request:[/error] {id}",
                            style="bold",
                        )
                        console.print(f"[error]{type(ex).__name__}:[/error] {str(ex)}")
                        failures.append(id)

                    progress.advance(task)

        # Print a summary
        summary = "---\n"
        if len(successes) > 0:
            summary += "**Re-running:**\n"
            for id in successes:
                summary += f"* {id}\n"
        if len(failures) > 0:
            summary += "\n**Failed to rerun:**\n"
            for id in failures:
                summary += f"* {id}\n"

        console.print(Markdown(summary))


class SearchSCC(Command):
    """
    Queries SCC for measurements

    scc-search
        {date-start : First day to return (YYYY-MM-DD)}
        {date-end : Last day to return (YYYY-MM-DD)}
        {--location=? : Search for measurement from this station}
        {--detailed-status : Get detailed status (exit codes) for each processing result. Must be used with --to-csv=}
        {--to-csv= : Optionally, write file list into a CSV file}
    """

    def handle(self):
        # Parse arguments
        location_name = self.option("location")
        location = None
        if location_name is not None:
            location = locations.LOCATIONS[location_name]
            if location is None:
                locations.unknown_location_error(location_name)
                return 1

        try:
            date_start = self.argument("date-start")
            date_start = datetime.date.fromisoformat(date_start)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        try:
            date_end = self.argument("date-end")
            date_end = datetime.date.fromisoformat(date_end)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        detailed_status = self.option("detailed-status")
        if detailed_status and (self.option("to-csv") is None):
            console.print(
                "[error]Cannot use --detailed-status without --to-csv=[/error]"
            )
            return 1

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Login to SCC to make queries
        with scc_session(credentials) as scc:
            with Progress(console=console) as progress:
                task = progress.add_task("Fetching results...", start=False, total=1)

                # Query SCC for measurements
                pages, measurements = scc.query_measurements(
                    date_start, date_end, location
                )
                if len(measurements) == 0:
                    progress.stop()
                    console.print("[warn]No measurements found![/warn]")
                    return 0

                progress.start_task(task)
                if pages > 1:
                    progress.update(task, total=pages, completed=1, start=True)

                    current_page = 2
                    while current_page <= pages:
                        _, more_measurements = scc.query_measurements(
                            date_start, date_end, location, page=current_page
                        )
                        measurements += more_measurements

                        current_page += 1
                        progress.advance(task)
                else:
                    progress.advance(task)

                # Download details if requested
                if detailed_status:
                    details = []
                    for m in progress.track(
                        measurements, description="Fetching procesing status codes..."
                    ):
                        details.append(scc.get_measurement(m.id))

        # Render table
        table = Table(show_header=True, header_style="bold")
        for col in [
            "ID",
            "Location",
            "Start",
            "End",
            "HiRELPP",
            "CloudMask",
            "ELPP",
            "ELDA",
            "ELDEC",
            "ELIC",
            "ELQUICK",
            "Is Processing",
        ]:
            table.add_column(col)

        for m in measurements:
            table.add_row(
                m.id,
                m.location.name,
                m.date_start.strftime("%Y-%m-%d %H:%M"),
                m.date_end.strftime("%Y-%m-%d %H:%M"),
                m.hirelpp.status.to_emoji(),
                m.cloudmask.status.to_emoji(),
                m.elpp.status.to_emoji(),
                m.elda.status.to_emoji(),
                m.eldec.status.to_emoji(),
                m.elic.status.to_emoji(),
                m.elquick.status.to_emoji(),
                m.is_processing.status.to_emoji(),
            )

        console.print(table)

        # Write to CSV
        csv_path = self.option("to-csv")
        if csv_path is not None:
            csv_path = Path(csv_path)
            if not detailed_status:
                with open(csv_path, "w") as f:
                    f.write(
                        "id,station_id,location,date_start,date_end,date_creation,date_updated,hirelpp,cloudmask,elpp,elda,eldec,elic,elquick,is_processing\n"
                    )

                    for m in measurements:
                        f.write(m.to_csv() + "\n")
            else:
                with open(csv_path, "w") as f:
                    f.write(
                        "station_id,location,date_start,date_end,date_creation,date_updated,upload,hirelpp,cloudmask,elpp,elic\n"
                    )

                    for m1, m2 in zip(measurements, details):
                        f.write(
                            f"{m1.id},{m1.location.name},{m1.station_code},{m1.date_start.isoformat()},{m1.date_end.isoformat()},{m1.date_creation.isoformat()},{m1.date_updated.isoformat()},{m2.is_uploaded.code},{m2.hirelpp.code},{m2.cloudmask.code},{m2.elpp.code},{m2.elic.code}\n"
                        )

            console.print(f"[info]Wrote .csv file[/info] {csv_path}")


class SearchDownloadSCC(Command):
    """
    Search SCC for products and downloads them into the given path

    scc-search-download
        {date-start : First day to return (YYYY-MM-DD)}
        {date-end : Last day to return (YYYY-MM-DD)}
        {download-path : Where to store the downloaded files}
        {--location=? : Search for measurement from this station}
        {--to-csv= : Optionally, write file list into a CSV file}
        {--no-hirelpp : Do not download HiRELPP products}
        {--no-cloudmask : Do not download cloudmask products}
        {--no-elpp : Do not download ELPP files}
        {--no-optical : Do not download optical (ELDA or ELDEC) files}
        {--no-elic : Do not download ELIC files}
    """

    def handle(self):
        # Parse arguments
        location_name = self.option("location")
        location = None
        if location_name is not None:
            location = locations.LOCATIONS[location_name]
            if location is None:
                locations.unknown_location_error(location_name)
                return 1

        try:
            date_start = self.argument("date-start")
            date_start = datetime.date.fromisoformat(date_start)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        try:
            date_end = self.argument("date-end")
            date_end = datetime.date.fromisoformat(date_end)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        hirelpp = option_to_bool(self.option("no-hirelpp"), True)
        cloudmask = option_to_bool(self.option("no-cloudmask"), True)
        elpp = option_to_bool(self.option("no-elpp"), True)
        optical = option_to_bool(self.option("no-optical"), True)
        elic = option_to_bool(self.option("no-elic"), True)

        download_path = Path(self.argument("download-path"))
        download_path.mkdir(exist_ok=True, parents=True)

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Login to SCC
        with scc_session(credentials) as scc:
            # Look up products
            with Progress(console=console) as progress:
                task = progress.add_task("Fetching results...", start=False, total=1)

                # Query SCC for measurements
                pages, measurements = scc.query_measurements(
                    date_start, date_end, location
                )
                if len(measurements) == 0:
                    progress.stop()
                    console.print("[warn]No measurements found![/warn]")
                    return 0

                if pages > 1:
                    progress.start_task(task)
                    progress.update(task, total=pages, completed=1, start=True)

                    current_page = 2
                    while current_page <= pages:
                        _, more_measurements = scc.query_measurements(
                            date_start, date_end, location, page=current_page
                        )
                        measurements += more_measurements

                        current_page += 1
                        progress.advance(task)

            console.log(
                f"[info]Found[/info] {len(measurements)} [info]measurements.[/info]"
            )

            # Download files
            measurement_count = len(measurements)
            file_count = 0
            i = 0
            with Progress(console=console) as progress:
                task = progress.add_task(
                    f"Downloading products (1/{measurement_count})...",
                    total=measurement_count,
                )

                for m in measurements:
                    progress.update(
                        task,
                        description=f"Downloading products ({i}/{measurement_count})...",
                    )
                    try:
                        for file in scc.download_products(
                            m.id,
                            download_path,
                            hirelpp and (m.hirelpp.status == ProductStatus.OK),
                            cloudmask and (m.cloudmask.status == ProductStatus.OK),
                            elpp and (m.elpp.status == ProductStatus.OK),
                            optical
                            and (
                                (m.elda.status == ProductStatus.OK)
                                or (m.eldec.status == ProductStatus.OK)
                            ),
                            elic and (m.elic.status == ProductStatus.OK),
                        ):
                            file_count += 1
                            console.log(f"[info]Downloaded[/info] {file}")
                    except ValueError:
                        console.log(
                            f"[error]Measurement[/error] {m.id} [error]has no products, skipping[/error]"
                        )
                    progress.advance(task)
                    i += 1

        console.log(f"[info]Downloaded[/info] {file_count} [info]files![/info]")


class LidarConstantsSCC(Command):
    """
    Downloads the table of lidar constants from SCC

    scc-lidar-constants
        {date-start : First day to return (YYYY-MM-DD)}
        {date-end : Last day to return (YYYY-MM-DD)}
        {csv : Where to write the table as a CSV file}
        {--location=? : Search for measurement from this station}
    """

    def handle(self):
        # Parse arguments
        location_name = self.option("location")
        location = None
        if location_name is not None:
            location = locations.LOCATIONS[location_name]
            if location is None:
                locations.unknown_location_error(location_name)
                return 1

        try:
            date_start = self.argument("date-start")
            date_start = datetime.date.fromisoformat(date_start)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        try:
            date_end = self.argument("date-end")
            date_end = datetime.date.fromisoformat(date_end)
        except ValueError:
            logging.error(
                "Could not parse date-start! Please use the ISO format (YYYY-MM-DD)"
            )
            return 1

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Login to SCC to make queries
        with scc_session(credentials) as scc:
            with Progress(console=console) as progress:
                task = progress.add_task("Fetching results...", start=False, total=1)

                # Query SCC for measurements
                pages, lidar_constants = scc.get_lidar_consants(
                    date_start, date_end, location
                )
                if len(lidar_constants) == 0:
                    progress.stop()
                    console.print("[warn]No data found![/warn]")
                    return 0

                console.print(f"[info]Found {pages} pages[/info]")
                progress.start_task(task)
                if pages > 1:
                    progress.update(task, total=pages, completed=1, start=True)

                    current_page = 2
                    while current_page <= pages:
                        _, more = scc.get_lidar_consants(
                            date_start, date_end, location, page=current_page
                        )
                        lidar_constants += more

                        current_page += 1
                        progress.advance(task)
                else:
                    progress.advance(task)

        # Write to CSV
        csv_path = self.argument("csv")
        csv_path = Path(csv_path)
        with open(csv_path, "w") as f:
            f.write(
                "measurement_id,channel_id,system_id,product_id,detection_wavelength,lidar_constant,lidar_constant_stat_err,profile_start_time,profile_end_time,calibration_window_bottom,calibration_window_top,creation_date,elda_version\n"
            )

            for c in lidar_constants:
                f.write(c.to_csv() + "\n")

            console.print(f"[info]Wrote .csv file[/info] {csv_path}")


class AutoUploadCalibration(Command):
    """
    Uploads a calibration file to SCC, checks results with qc-eldec and if the QC checks do not pass, deletes the file

    scc-auto-upload-calibration
        {path : Path to calibration file}
        {location : Location to use for QC-ELDEC history}
        {--plot= : Where to store the calibration plots}
    """

    help = """
    Use this command for automatic the upload of QC-checked calibration files to SCC. It
    performs the following actions:

    - Uploads the given calibration file to SCC
    - Waits for SCC to produce the ELDEC product
    - Downloads the ELDEC product
    - Runs QC check
    - If the QC check fails, deletes the calibration file from SCC

    The program will wait up to 5 minutes for the ELDEC product to be produced. If SCC
    takes longer, it will timeout and the program will exit.
    """

    def handle(self):
        # Parse arguments
        path = self.argument("path")
        path = Path(path)
        if not path.exists() and not path.is_file():
            console.print(f"[error]{path} does not exist![/error]")
            return 1

        location_name = self.argument("location")
        location = locations.LOCATIONS.get(location_name, None)
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        temp_path = Path(tempfile.gettempdir()) / f"pollyxt_pipelines-{os.getpid()}"
        try:
            temp_path.mkdir(parents=True, exist_ok=True)
            console.print(
                f"[info]Using directory for temporary files: [/info]{temp_path}"
            )
        except:
            console.print(
                "[error]Could not create temporary directory: [/error]{temp_path}"
            )
            console.print_exception()

        # Read application config
        config = Config()
        try:
            credentials = SCC_Credentials(config)
        except KeyError:
            print_login_error()
            return 1

        # Read configuration and measurement IDs from netCDF file
        try:
            with Dataset(path, "r") as nc:
                configuration_id = nc.X_PollyXTPipelines_Configuration_ID
                measurement_id = nc.Measurement_ID
        except Exception as ex:
            console.print("[error]Could not read configuration ID from file![/error]")
            console.print_exception(ex)
            return 1

        with scc_session(credentials) as scc:
            # Upload calibration file
            try:
                scc.upload_file(path, system_id=configuration_id)
                console.print(
                    f"Uploaded [info]{measurement_id}[/info] with configuration ID [info]{configuration_id}[/info]"
                )
            except Exception:
                console.print(
                    f"[error]Could not upload calibration file {path}:[/error]"
                )
                console.print_exception()
                return 1

            with console.status(
                "[bold green] Waiting for SCC to create ELDEC product..."
            ) as status:
                # Check calibration file
                timeout_timer = 0
                while True:
                    measurement = scc.get_measurement(measurement_id)
                    # If the file is not waiting for processing and is not currently processing,
                    # the products should be ready.
                    if not measurement.is_processing and not measurement.is_queued:
                        if measurement.eldec.status == ProductStatus.OK:
                            break
                        else:
                            status.stop()
                            console.print(
                                f"[error]SCC could not process uploaded file."
                            )
                            return 1

                    elif timeout_timer >= 60 * 5:
                        status.stop()
                        console.print(
                            f"[error]ELDEC product timed out after 5 minutes![/error]"
                        )
                        console.print(
                            f"You should check what happened to the file manually."
                        )
                        return 1

                    time.sleep(30)
                    timeout_timer += 30

            # Download EDLEC file
            console.print("Downloading ELDEC product...")
            try:
                eldec_zip_path = list(
                    scc.download_products(
                        measurement_id,
                        temp_path,
                        hirelpp=False,
                        cloudmask=False,
                        elpp=False,
                        optical=True,
                        elic=False,
                    )
                )[0]
            except Exception:
                status.stop()
                console.print("[error]Error in ELDEC product download[/error]")
                console.print_exception()
                return 1

            # Unzip ELDEC product
            console.print("Unzipping ELDEC product...")
            with zipfile.ZipFile(eldec_zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_path)

            # Run QC check
            eldec_files = list((temp_path / measurement_id).glob("*_eldec_v*.nc"))
            console.print(f"[info]Found {len(eldec_files)} ELDEC files[/info]")
            for eldec_file in eldec_files:
                console.print(f"Running QC check on {eldec_file.name}...")
                eldec = qc_eldec_file.ELDECfile(
                    eldec_file, location, plot_path=self.option("plot")
                )

                # Delete calibration file in case of bad QC check
                if not eldec.calibration_ok():
                    console.print(
                        f"[bold red] File {eldec_file.name} did not pass QC check! Deleting {measurement_id}"
                    )
                    try:
                        scc.delete_measurement(measurement_id)
                        console.print("Deleted!")
                    except Exception:
                        console.print(
                            f"[error]Error in deleting measurement[/error] {measurement_id}"
                        )
                        console.print_exception()
                    return 1

                console.print(f"[info]{eldec_file.name} passed QC check![/info]")

        # Clean up temp files
        shutil.rmtree(temp_path)