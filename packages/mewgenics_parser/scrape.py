"""Script to scrape Mewgenics Wiki and generate Python constant sets."""

import re
from textwrap import dedent

import requests
from bs4 import BeautifulSoup

import mewgenics_parser

BASE_URL = "https://mewgenics.wiki.gg"
GAME_DATA = mewgenics_parser.GameData.from_gpak(
    r"C:\Program Files (x86)\Steam\steamapps\common\Mewgenics\resources.gpak"
)

def name_to_id(name: str) -> str:
    if (candidate_id := name.replace(" ", "")) in GAME_DATA.ability_text:
        return candidate_id

    for id_, name_and_description in GAME_DATA.ability_text.items():
        if name_and_description.name == name:
            return id_
    raise ValueError(f"Name '{name}' not found in game data.")


def extract_table_rows(table) -> list[dict]:
    """Extract rows from a wikitable into a list of dictionaries based on headers."""
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    if not headers:
        first_row = table.find("tr")
        if not first_row:
            return []
        headers = [td.get_text(strip=True) for td in first_row.find_all(["td", "th"])]
        rows = table.find_all("tr")[1:]
    else:
        rows = [
            tr
            for tr in table.find_all("tr")
            if not all(c.name == "th" for c in tr.find_all(["td", "th"]))
        ]

    data = []
    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue

        row_data = {}
        for i, col in enumerate(cols):
            if i < len(headers):
                text = col.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)
                row_data[headers[i]] = text

        if row_data:
            data.append(row_data)

    return data


def scrape_disorders() -> set[str]:
    """Scrape the Disorders page and return normalized names."""
    resp = requests.get(f"{BASE_URL}/wiki/Disorders")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    disorders = set()
    for table in soup.find_all("table", class_="wikitable"):
        for row_data in extract_table_rows(table):
            name = row_data.get("Name", "")
            if name:
                disorders.add(name_to_id(name))

    return disorders


def scrape_collarless() -> tuple[set[str], set[str]]:
    """Scrape the Collarless page for abilities and passives."""
    resp = requests.get(f"{BASE_URL}/wiki/Collarless")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    basic_attacks = set()
    abilities = set()
    passives = set()

    for table in soup.find_all("table", class_="wikitable"):
        rows = extract_table_rows(table)
        if not rows:
            continue

        headers = list(rows[0].keys())

        if any("Active" in header for header in headers):
            # Active Abilities Table
            for row in rows:
                name = row.get("Name", "")
                if name:
                    abilities.add(name_to_id(name))
        elif any("Passive" in header for header in headers):
            # Passives Table
            for row in rows:
                name = row.get("Name", "")
                if name:
                    passives.add(name_to_id(name))

    return abilities, passives


def generate_python_code(
    disorders: set[str], abilities: set[str], passives: set[str]
) -> str:
    """Format the sets into a copy-pasteable Python snippet."""

    def format_set(name: str, items: set[str]) -> str:
        sorted_items = sorted(list(items))
        items_str = ", ".join(f'"{item}"' for item in sorted_items)

        return dedent(f"""\
        {name} = frozenset(
            {{
                {items_str}
            }}
        )
        """)

    code = []

    code.append("# Generic spells available to all cats (collarless/generic)")
    code.append(format_set("COLLARLESS_SPELLS", abilities))

    code.append("# Generic passives available to all cats (collarless/generic)")
    code.append(format_set("COLLARLESS_PASSIVES", passives))

    code.append("# Birth defects (NOT passives, NOT inheritable via passive mechanics)")
    code.append(format_set("DISORDERS", disorders))

    return "\n".join(code)


def main():
    """Run the scraper and print Python constants."""
    disorders = scrape_disorders()
    abilities, passives = scrape_collarless()
    print(generate_python_code(disorders, abilities, passives))


if __name__ == "__main__":
    main()
