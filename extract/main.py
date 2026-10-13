import requests
import pandas as pd
import hashlib
import json

from datetime import datetime

API_BASE_URL = "https://f1fantasytools.com/api/statistics"

from pathlib import Path

#Project Root
BASE_DIR = Path(__file__).resolve().parent.parent

# table dir
TABLE_DIR = BASE_DIR / "tables"

# extract dir
EXTRACT_DIR = BASE_DIR / "extract"

# asset dir
DRIVER_DIR = TABLE_DIR / "drivers"
CONSTRUCTOR_DIR = TABLE_DIR / "constructors"

# Extract files
HASH_FILE = EXTRACT_DIR / "hashes.json"
CONFIG_FILE = BASE_DIR / "config.yml"


def build_year(year):

    driver_records = []
    constructor_records = []

    url = f"{API_BASE_URL}/{year}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    data = response.json()

    season = data["seasonResult"]
    races = season["raceResults"]

    for race_number, race_data in races.items():

        for driver in race_data.get("drivers", []):
            driver_records.append({
                "year": year,
                "race": int(race_number),
                **driver
            })

        for constructor in race_data.get("constructors", []):
            constructor_records.append({
                "year": year,
                "race": int(race_number),
                **constructor
            })

    drivers_df = pd.json_normalize(driver_records, sep="_")
    constructors_df = pd.json_normalize(
        constructor_records,
        sep="_"
    )

    print("Drivers:", drivers_df.shape)
    print("Constructors:", constructors_df.shape)

    return drivers_df, constructors_df



def hash(drivers: pd.DataFrame, constructors: pd.DataFrame) -> str:

    # Ensure consistent row ordering
    drivers = drivers.sort_values(["year", "race", "id"])
    constructors = constructors.sort_values(["year", "race", "id"])

    # Hash each DataFrame
    driver_hash = pd.util.hash_pandas_object(drivers, index=False)
    constructor_hash = pd.util.hash_pandas_object(constructors, index=False)

    # Combine the hashes
    combined = (
        driver_hash.to_numpy(dtype="uint64").tobytes()
        + constructor_hash.to_numpy(dtype="uint64").tobytes()
    )

    return hashlib.sha256(combined).hexdigest()


def compare_hashes(year, new_hash):
    """
    Returns True if the hash is new or has changed.
    Returns False if the hash matches the stored hash.
    """

    # If the file doesn't exist, all hashes are new
    if not HASH_FILE.exists():
        return True

    with HASH_FILE.open("r") as f:
        hashes = json.load(f)

    # If the year doesn't exist, return True
    if str(year) not in hashes:
        return True

    old_hash = hashes[str(year)]

    return old_hash != new_hash


def update_hash(year, new_hash):

    with HASH_FILE.open("r") as f:
        hashes = json.load(f)

    hashes[str(year)] = new_hash

    with HASH_FILE.open("w") as f:
        json.dump(hashes, f, indent=4)


def main():

    years = list(range(2023, datetime.now().year + 1))

    for year in years:
        
        driver_table, constructor_table = build_year(year)

        new_hash = hash(drivers=driver_table, constructors=constructor_table)

        if compare_hashes(year, new_hash):

            #new hash

            # create the directories if needed
            DRIVER_DIR.mkdir(parents=True, exist_ok=True)
            CONSTRUCTOR_DIR.mkdir(parents=True, exist_ok=True)

            # save the new dfs
            driver_table.to_csv(DRIVER_DIR / f"driver_{year}.csv", index=False)
            constructor_table.to_csv(CONSTRUCTOR_DIR / f"constructor_{year}.csv", index=False)

            #update the hash
            update_hash(year, new_hash)


if __name__ == "__main__":
    main()