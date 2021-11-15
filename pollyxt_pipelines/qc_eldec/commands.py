"""
Commands for performing the QC check on ELDEC products
"""

from cleo import Command

from pollyxt_pipelines import locations
from pollyxt_pipelines.qc_eldec import qc_eldec_file


class QCEldec(Command):
    """Perform calibration QC check on ELDEC files

    qc-eldec
        {input : Path to ELDEC file}
        {location : Which location does this calibration file come from.}
        {plot? : Optionally, a path to store the plot}
    """

    def handle(self):
        # Get arguments
        input_file = self.argument("input")
        plot_path = self.argument("plot")

        location_name = self.argument("location")
        location = locations.LOCATIONS[location_name]
        if location is None:
            locations.unknown_location_error(location_name)
            return 1

        # Execute check
        eldec = qc_eldec_file.ELDECfile(input_file, location, plot_path=plot_path)
        if eldec.calibration_ok():
            self.line("Calibration OK!")
            return 0

        self.line("Calibration does not pass checked.")
        return 1
