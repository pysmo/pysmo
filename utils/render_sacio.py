from pysmo.lib.defaults import SACIO_DEFAULTS
from jinja2 import Environment, FileSystemLoader
import os
import yaml
from black import FileMode, format_file_contents

MYDIR = os.path.dirname(__file__)

# skip these from being rendered automatically and define
# them in the template file directly
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

validators = dict(
    stla="validators.optional([type_validator(), validators.ge(-90), validators.le(90)])",  # noqa: E501
    stlo="validators.optional([type_validator(), validators.gt(-180), validators.le(180)])",  # noqa: E501
    evla="validators.optional([type_validator(), validators.ge(-90), validators.le(90)])",  # noqa: E501
    evlo="validators.optional([type_validator(), validators.gt(-180), validators.le(180)])",  # noqa: E501
)

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

    if "allowed_vals" in header_dict:
        headers[header]["python_type"] = "str"
        headers[header]["is_enum"] = True
        if hasattr(SACIO_DEFAULTS, header):
            validators[header] = "validate_sacenum"
        else:
            validators[header] = "validators.optional(validate_sacenum)"
    elif header_type == "f":
        headers[header]["python_type"] = "float"
    elif header_type == "n":
        headers[header]["python_type"] = "int"
    elif header_type == "i":
        headers[header]["python_type"] = "str"
    elif header_type == "k":
        headers[header]["python_type"] = "str"
    elif header_type == "l":
        headers[header]["python_type"] = "bool"


environment = Environment(loader=FileSystemLoader(os.path.join(MYDIR, "templates/")))
template = environment.get_template("sacio-template.py.j2")
outfile = "sacio.py"

# remove 'a' since it doesn't make sense here
header_types.pop("a")

content = template.render(
    headers=headers,
    footers=footers,
    header_types=header_types,
    enum_dict=enum_dict,
    properties=properties,
    validators=validators,
    sacio_defaults=SACIO_DEFAULTS,
)

content = format_file_contents(content, fast=False, mode=FileMode())

with open(outfile, mode="w", encoding="utf-8") as sacio:
    sacio.write(content)
