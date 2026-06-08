import os
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import random

USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",

    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",

    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",

    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",

    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
]

session = requests.Session()
session.headers.update({
    "User-Agent": random.choice(USER_AGENTS),
})


def alt_to_score(alt):
    if not alt:
        return None

    try:
        return int(str(alt).split()[0])
    except Exception:
        return None


def get_score_alts(address):
    url = "https://www.walkscore.com/score/" + quote_plus(address)

    response = session.get(url, timeout=15)

    if response.status_code != 200:
        raise Exception(f"Status code {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        "walk_score_alt": None,
        "transit_score_alt": None,
        "bike_score_alt": None,
    }

    score_divs = soup.find_all(
        "div",
        class_=lambda c: c and "clearfix" in c and "score-div" in c
    )

    for div in score_divs:
        imgs = div.find_all("img", alt=True)

        for img in imgs:
            alt = img.get("alt", "").strip()

            if "Walk Score" in alt:
                result["walk_score_alt"] = alt

            elif "Transit Score" in alt:
                result["transit_score_alt"] = alt

            elif "Bike Score" in alt:
                result["bike_score_alt"] = alt

    result["walkscore"] = alt_to_score(result["walk_score_alt"])
    result["transitscore"] = alt_to_score(result["transit_score_alt"])
    result["bikescore"] = alt_to_score(result["bike_score_alt"])

    return result


def format_address(address):
    postfix = " EDMONTON AB CANADA"

    return (
        (str(address).strip() + postfix)
        .lower()
        .replace("street", "st")
        .replace("avenue", "ave")
        .replace("road", "rd")
        .replace(" ", "-")
    )

def scrape_scores(df, output_file, address_col="address", save_every=100):
    df = df.copy()

    # Continue mode: load existing checkpoint/output if it exists
    if os.path.exists(output_file):
        print(f"Continuing from checkpoint: {output_file}")
        saved_df = pd.read_csv(output_file)

        for col in ["walkscore", "transitscore", "bikescore"]:
            if col in saved_df.columns:
                df[col] = saved_df[col]
            else:
                df[col] = np.nan
    else:
        df["walkscore"] = np.nan
        df["transitscore"] = np.nan
        df["bikescore"] = np.nan

    total_rows = len(df)
    start_time = time.time()
    done_count = 0

    for i, row in df.iterrows():

        # Skip already completed rows
        if (
            pd.notna(df.at[i, "walkscore"]) or
            pd.notna(df.at[i, "transitscore"]) or
            pd.notna(df.at[i, "bikescore"])
        ):
            continue

        # time.sleep(random.uniform(0.1, 1.0))  # Polite delay

        address = row[address_col]
        full_address = format_address(address)

        try:
            scores = get_score_alts(full_address)

            df.at[i, "walkscore"] = scores["walkscore"]
            df.at[i, "transitscore"] = scores["transitscore"]
            df.at[i, "bikescore"] = scores["bikescore"]

        except Exception as e:
            print(f"\nError on {address}: {e}")

        completed = i + 1
        done_count += 1

        elapsed = time.time() - start_time
        avg_time = elapsed / max(done_count, 1)

        remaining = total_rows - completed
        eta_seconds = remaining * avg_time
        finish_time = datetime.now() + timedelta(seconds=eta_seconds)

        pct = completed / total_rows * 100

        bar_len = 30
        filled = int(bar_len * completed / total_rows)
        bar = "█" * filled + "-" * (bar_len - filled)

        print(
            f"\r[{bar}] "
            f"{completed}/{total_rows} "
            f"({pct:.1f}%) | "
            f"Avg: {avg_time:.2f}s/row | "
            f"ETA: {timedelta(seconds=int(eta_seconds))} | "
            f"Finish: {finish_time.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{full_address[:50]}{' ' * 10}",
            end="",
            flush=True
        )

        if completed % save_every == 0:
            df.to_csv(output_file, index=False)
            print(f"\nCheckpoint saved: {completed} rows -> {output_file}")

    df.to_csv(output_file, index=False)
    print(f"\nFinal saved: {len(df)} rows -> {output_file}")


if __name__ == "__main__":

    train = pd.read_csv(
        "./data/clean/honestdoor_property_details_clean.csv"
    )

    # test = pd.read_csv(
    #     "./data/clean/honestdoor_listing_details_clean.csv"
    # )

    scrape_scores(
        train,
        "./data/train/data.csv",
        address_col="address",
    )

    # scrape_scores(
    #     test,
    #     "./data/test/test.csv",
    #     address_col="address",
    # )