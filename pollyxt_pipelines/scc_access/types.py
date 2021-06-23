"""
Various container classes and utility functions for handling SCC responses
"""

from typing import Dict, Any, NamedTuple, Union
from enum import Enum, auto

from datetime import datetime
from dataclasses import dataclass, field
from bs4.element import Tag

from pollyxt_pipelines.locations import Location, get_location_by_scc_code


# ## Utility function for HTML parsing


class ProductStatus(Enum):
    """
    Represents the status of a product (ie ELDA) on SCC
    """

    OK = auto()
    ERROR = auto()
    NO_RUN = auto()
    UNKNOWN = auto()

    def to_emoji(self):
        """
        Converts the given status to emoji.

        Contains color tags for use with the `rich` library.
        """

        if self == ProductStatus.OK:
            return "[green]✔[/green]"
        if self == ProductStatus.ERROR:
            return "[red]✘[/red]"
        if self == ProductStatus.NO_RUN:
            return "∅"
        if self == ProductStatus.UNKNOWN:
            return "❓"

        raise ValueError("Enum has unknown value!")


class Product:
    status: ProductStatus
    code: Union[int, None]

    def __init__(self, status: ProductStatus, code=None) -> None:
        self.status = status
        self.code = code

    @staticmethod
    def from_code(code: int):
        return Product(code == 127, code)


def scc_date(tag: Tag) -> datetime:
    """Convert a table cell to a date"""
    return datetime.strptime(tag.text, "%Y-%m-%d %H:%M")


def scc_product_status(node: Tag) -> Product:
    """Convert a table cell to a Product. Preserves all states (OK, NO_RUN, ERROR)."""

    # Check tristate
    alt = node.img["alt"]
    if alt == "OK":
        return Product(ProductStatus.OK)
    elif alt == "Not Executed":
        return Product(ProductStatus.NO_RUN)
    elif alt == "Error":
        return Product(ProductStatus.ERROR)

    return Product(ProductStatus.UNKNOWN)


def scc_bool(node: Tag) -> bool:
    """Convert a table cell to a bool"""
    alt = node.img["alt"]

    if alt == "True":
        return Product(ProductStatus.OK)
    elif alt == "False":
        return Product(ProductStatus.ERROR)

    return Product(ProductStatus.UNKNOWN)


# ## Container classes


@dataclass(frozen=True)
class Measurement:
    id: str
    station_code: str
    location: Location = field(init=False)

    date_start: datetime
    date_end: datetime
    date_creation: datetime
    date_updated: datetime

    is_uploaded: Product
    hirelpp: Product
    cloudmask: Product
    elpp: Product
    elda: Product
    eldec: Product
    elic: Product
    elquick: Product

    is_processing: bool

    def __post_init__(self):
        super().__setattr__("location", get_location_by_scc_code(self.station_code))

    def to_csv(self):
        return f"{self.id},{self.location.name},{self.station_code},{self.date_start.isoformat()},{self.date_end.isoformat()},{self.date_creation.isoformat()},{self.date_updated.isoformat()},{self.is_uploaded.status.name},{self.hirelpp.status.name},{self.cloudmask.status.name},{self.elpp.status.name},{self.elda.status.name},{self.eldec.status.name},{self.elic.status.name},{self.elquick.status.name}"

    @staticmethod
    def from_table_row(tr: Tag):
        """
        Create a measurement object from a table row.
        Table rows are formatted like in https://scc.imaa.cnr.it/admin/database/measurements/
        """

        # print(tr.prettify())

        return Measurement(
            id=tr.find("td", class_="field-id").text,
            station_code=tr.find("th", class_="field-station_id").a.text,
            date_start=scc_date(tr.find("td", class_="field-start")),
            date_end=scc_date(tr.find("td", class_="field-stop")),
            date_creation=scc_date(tr.find("td", class_="field-creation_date")),
            date_updated=scc_date(tr.find("td", class_="field-updated_date")),
            is_uploaded=scc_product_status(tr.find("td", class_="field-upload_ok_evo")),
            hirelpp=scc_product_status(tr.find("td", class_="field-hirelpp_ok_evo")),
            cloudmask=scc_product_status(tr.find("td", class_="field-cloudmask_ok_evo")),
            elpp=scc_product_status(tr.find("td", class_="field-elpp_ok_evo")),
            elda=scc_product_status(tr.find("td", class_="field-elda_ok_evo")),
            eldec=scc_product_status(tr.find("td", class_="field-eldec_ok_evo")),
            elic=scc_product_status(tr.find("td", class_="field-elic_ok_evo")),
            elquick=scc_product_status(tr.find("td", class_="field-elquick_ok_evo")),
            is_processing=scc_bool(tr.find("td", class_="field-is_being_processed")),
        )

    @staticmethod
    def from_json(json: Dict[str, any]):
        return Measurement(
            id=json["id"],
            station_code=None,
            date_start=datetime.fromisoformat(json["start"]),
            date_end=datetime.fromisoformat(json["stop"]),
            date_creation=None,
            date_updated=None,
            is_uploaded=Product.from_code(json["upload"]),
            hirelpp=Product.from_code(json["hirelpp"]),
            cloudmask=Product.from_code(json["cloudmask"]),
            elpp=Product.from_code(json["elpp"]),
            elda=None,
            eldec=None,
            elic=Product.from_code(json["elic"]),
            elquick=None,
            is_processing=json["is_running"],
        )


@dataclass(frozen=True)
class LidarConstant:
    measurement_id: str
    channel_id: str
    system_id: str
    product_id: str

    detection_wavelength: str
    lidar_constant: str
    lidar_constant_stat_err: str

    profile_start_time: datetime
    profile_end_time: datetime

    calibration_window_bottom: str
    calibration_window_top: str

    creation_date: datetime
    elda_version: str

    def to_csv(self):
        return f"{self.measurement_id},{self.channel_id},{self.system_id},{self.product_id},{self.detection_wavelength},{self.lidar_constant},{self.lidar_constant_stat_err},{self.profile_start_time},{self.profile_end_time},{self.calibration_window_bottom},{self.calibration_window_top},{self.creation_date},{self.elda_version}"

    @staticmethod
    def from_table_row(tr: Tag):
        """
        Create a measurement object from a table row.
        Table rows are formatted like in https://scc.imaa.cnr.it/admin/database/lidarconstant/
        """

        # print(tr.prettify())

        return LidarConstant(
            measurement_id=tr.find("td", class_="field-measurement_id_display").text,
            channel_id=tr.find("td", class_="field-channel_id_display").text,
            system_id=tr.find("td", class_="field-system_id_display").text,
            product_id=tr.find("td", class_="field-product_id_display").text,
            detection_wavelength=tr.find("td", class_="field-detection_wavelength").text,
            lidar_constant=tr.find("td", class_="field-lidar_constant").text,
            lidar_constant_stat_err=tr.find("td", class_="field-lidar_constant_stat_err").text,
            profile_start_time=scc_date(tr.find("td", class_="field-profile_start_time")),
            profile_end_time=scc_date(tr.find("td", class_="field-profile_end_time")),
            calibration_window_bottom=tr.find("td", class_="field-calibr_window_bottom").text,
            calibration_window_top=tr.find("td", class_="field-calibr_window_top").text,
            creation_date=scc_date(tr.find("td", class_="field-creation_date")),
            elda_version=tr.find("td", class_="field-elda_version").text,
        )


class APIObject:
    """
    SCC generic API response object

    The only objects fetched from the API are Anchillary files, so this
    class doesn't do much.
    """

    """True if the object exists on SCC"""
    exists: bool

    def __init__(self, response_body: Union[Dict[str, Any], None]):
        if response_body is not None:
            for key, value in response_body.items():
                setattr(self, key, value)
            self.exists = self.status != "missing"
        else:
            self.exists = False
