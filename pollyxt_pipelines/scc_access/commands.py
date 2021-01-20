import logging
import datetime
import getpass
from pathlib import Path

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
from pollyxt_pipelines.utils import bool_to_emoji, option_to_bool


class Login(Command):
    """
    Provide the necessary credentials for authenticating with SCC

    login
    """

    def handle(self):
        # Print warning!
        path = config_paths()[-1]
        warning_md = "Your credentials will be stored as **PLAIN-TEXT** in the following file:\n"
        warning_md += f"\n* {path}\n"
        warning_md += "\nPlease make sure you understand the security implications of this and keep the config files safe!"
        warning_md = Markdown(warning_md)

        console.print(Panel(warning_md))

        # Ask for the credentials
        console.print(
            "Please enter the HTTP authentication credentials (this is the first login popup when you access the website):"
        )
        console.print("[warn]The password won't be visible while you are typing![/warn]")
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
        {list? : Optionally, store the uploaded file IDs in order to later download the products using scc-download}
    """

    def handle(self):
        # Parse arguments
        path = Path(self.argument("path"))
        if path.is_dir:
            files = path.glob("*.nc")
            files = filter(lambda x: not x.name.startswith("rs_"), files)
            files = filter(
                lambda x: not x.name.startswith("calibration_"), files
            )  # TODO Handle calibration files
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
                configuration_id = nc.NOAReACT_Configuration_ID
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
                    console.print(f"[error]Unknown error while uploading[/error] {file}")
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
                self.line_error("Either a list file or some measurement IDs must be provided!")
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
                    console.print(f"[warn]File[/warn] {id} [warn]is still processing.[/warn]")
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
                        console.print(f"-> [error]Could not delete:[/error] {id}", style="bold")
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
                            f"-> [error]Could not make request:[/error] {id}", style="bold"
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
            logging.error("Could not parse date-start! Please use the ISO format (YYYY-MM-DD)")
            return 1

        try:
            date_end = self.argument("date-end")
            date_end = datetime.date.fromisoformat(date_end)
        except ValueError:
            logging.error("Could not parse date-start! Please use the ISO format (YYYY-MM-DD)")
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
                pages, measurements = scc.query_measurements(date_start, date_end, location)
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
                bool_to_emoji(m.has_hirelpp),
                bool_to_emoji(m.has_cloudmask),
                bool_to_emoji(m.has_elpp),
                bool_to_emoji(m.has_elda),
                bool_to_emoji(m.has_eldec),
                bool_to_emoji(m.has_elic),
                bool_to_emoji(m.has_elquick),
                bool_to_emoji(m.is_processing),
            )

        console.print(table)

        # Write to CSV
        csv_path = self.option("to-csv")
        if csv_path is not None:
            csv_path = Path(csv_path)
            with open(csv_path, "w") as f:
                f.write(
                    "id,station_id,location,date_start,date_end,date_creation,date_updated,hirelpp,cloudmask,elpp,elda,eldec,elic,elquick,is_processing\n"
                )

                for m in measurements:
                    f.write(m.to_csv() + "\n")

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
            logging.error("Could not parse date-start! Please use the ISO format (YYYY-MM-DD)")
            return 1

        try:
            date_end = self.argument("date-end")
            date_end = datetime.date.fromisoformat(date_end)
        except ValueError:
            logging.error("Could not parse date-start! Please use the ISO format (YYYY-MM-DD)")
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
                pages, measurements = scc.query_measurements(date_start, date_end, location)
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

            console.log(f"[info]Found[/info] {len(measurements)} [info]measurements.[/info]")

            # Download files
            measurement_count = len(measurements)
            file_count = 0
            i = 0
            with Progress(console=console) as progress:
                task = progress.add_task(
                    f"Downloading products (1/{measurement_count})...", total=measurement_count
                )

                for m in measurements:
                    progress.update(
                        task, description=f"Downloading products ({i}/{measurement_count})..."
                    )
                    try:
                        for file in scc.download_products(
                            m.id,
                            download_path,
                            hirelpp and m.has_hirelpp,
                            cloudmask and m.has_cloudmask,
                            elpp and m.has_elpp,
                            optical and (m.has_elda or m.has_eldec),
                            elic and m.has_elic,
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
