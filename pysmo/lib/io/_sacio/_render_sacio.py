from pysmo.lib.io._sacio._lib import SACIO_DEFAULTS
from jinja2 import Environment, FileSystemLoader
import os
import yaml
from black import FileMode, format_file_contents

MYDIR = os.path.dirname(__file__)

# skip these from being rendered automatically and define
# them in sacio.py directly
properties = [
    "depmin",
    "depmax",
    "e",
    "dist",
    "az",
    "baz",
    "gcarc",
    "depmen",
    "xminimum",
    "xmaximum",
    "yminimum",
    "ymaximum",
    "npts",
    "nxsize",
    "nysize",
    "lcalda",
]

time_headers = [
    "b",
    "e",
    "o",
    "a",
    "f",
    "t0",
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "t8",
    "t9",
]

# Read yaml file with dictionaries describing SAC headers
with open(os.path.join(MYDIR, "sacheader.yml"), "r") as stream:
    _HEADER_DEFS: dict = yaml.safe_load(stream)

# Dictionary of header types (default values etc)
header_types: dict = _HEADER_DEFS.pop("header_types")
# Dictionary of header fields (format, type, etc)
headers: dict = _HEADER_DEFS.pop("header_fields")
# Dictionary of footer fields (format, type, etc)
footers: dict = _HEADER_DEFS.pop("footer_fields")
# Dictionary of enumerated headers (to convert int to str).
enum_dict: dict = _HEADER_DEFS.pop("enumerated_header_values")

# Add extra fields to headers dictionary if they aren't there
for header, header_dict in headers.items():
    header_type = header_dict["header_type"]
    if "format" not in header_dict:
        default_format_for_type = header_types[header_type]["format"]
        headers[header]["format"] = default_format_for_type

    if "length" not in header_dict:
        default_length_for_type = header_types[header_type]["length"]
        headers[header]["length"] = default_length_for_type

    if "allowed_vals" in header_dict:  # this means we are an enum header
        headers[header]["python_type"] = "str"
        headers[header]["is_enum"] = True
        headers[header]["validators"] = ["validate_sacenum"]
    elif header_type == "f":
        headers[header]["python_type"] = "float"
        headers[header]["converter"] = "float"
        headers[header]["validators"] = ["type_validator()"]
        if header in time_headers:
            headers[header]["validators"].append("validate_with_iztype")
    elif header_type == "n":
        headers[header]["python_type"] = "int"
        headers[header]["validators"] = ["type_validator()"]
    elif header_type == "i":
        headers[header]["python_type"] = "str"
        headers[header]["validators"] = [
            "type_validator()",
            f"validators.max_len({headers[header]['length']})",
        ]
    elif header_type == "k":
        headers[header]["python_type"] = "str"
        headers[header]["validators"] = [
            "type_validator()",
            f"validators.max_len({headers[header]['length']})",
        ]
    elif header_type == "l":
        headers[header]["python_type"] = "bool"
        headers[header]["validators"] = ["type_validator()"]

# override default validators
headers["stla"]["validators"] = [
    "type_validator()",
    "validators.ge(-90)",
    "validators.le(90)",
]
headers["stlo"]["validators"] = [
    "type_validator()",
    "validators.ge(-180)",
    "validators.le(180)",
]
headers["evla"]["validators"] = [
    "type_validator()",
    "validators.ge(-90)",
    "validators.le(90)",
]
headers["evlo"]["validators"] = [
    "type_validator()",
    "validators.ge(-180)",
    "validators.le(180)",
]

# remove 'a' since it doesn't make sense here
header_types.pop("a")

environment = Environment(loader=FileSystemLoader(MYDIR))
template = environment.get_template("sacio-template.py.j2")
outfile = os.path.join(MYDIR, "_sacio_rendered.py")

content = template.render(
    headers=headers,
    footers=footers,
    header_types=header_types,
    enum_dict=enum_dict,
    properties=properties,
    time_headers=time_headers,
    sacio_defaults=SACIO_DEFAULTS,
)

content = format_file_contents(content, fast=False, mode=FileMode())

with open(outfile, mode="w", encoding="utf-8") as sacio:
    sacio.write(content)
