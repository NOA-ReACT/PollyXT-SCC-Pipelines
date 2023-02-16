from enum import IntEnum


class Wavelength(IntEnum):
    """Laser wavelength"""

    NM_355 = 355
    NM_532 = 532
    NM_1064 = 1064


class Atmosphere(IntEnum):
    """
    Which atmosphere to use to processing. These are the possible values for `molecular_calc`.
    """

    AUTOMATIC = 0
    RADIOSONDE = 1
    CLOUDNET = 2
    STANDARD_ATMOSPHERE = 4

    @staticmethod
    def from_string(x: str):
        x = x.lower().strip()
        if x == "automatic":
            return Atmosphere.AUTOMATIC
        if x == "radiosonde":
            return Atmosphere.RADIOSONDE
        if x == "cloudnet":
            return Atmosphere.CLOUDNET
        if x == "standard":
            return Atmosphere.STANDARD_ATMOSPHERE

        raise ValueError(f"Unknown atmosphere {x}")
