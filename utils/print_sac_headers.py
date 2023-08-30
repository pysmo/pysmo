from pysmo.lib.io.sacio import _HEADER_FIELDS  # type: ignore


for name, header_data in _HEADER_FIELDS.items():
    print(f"{name}: {header_data.get('description')}")
