import importlib.resources
import json
import pathlib

with importlib.resources.open_text("Data", pathlib.Path("EN.json")) as json_data:
    locale_data = json.load(json_data)

with importlib.resources.open_text("Data", pathlib.Path("schema.sql")) as schema_data:
    schema = schema_data.read()
    print("SCHEMA", schema)

DATABASE = "./NN.db"
