# Data Loading, Cleaning, and Merging Script

# Import necessary libraries
import pandas as pd
import nflreadpy
import requests
from bs4 import BeautifulSoup

# Function to load play-by-play data using nflreadpy
def load_pbp_data(start_year, end_year):
    pbp_list = []
    for year in range(start_year, end_year + 1):
        print(f"Loading play-by-play data for {year}...")
        season_data = nflreadpy.load_pbp(year).to_pandas()
        pbp_list.append(season_data)
    pbp = pd.concat(pbp_list, ignore_index=True)
    print(f"Loaded {len(pbp):,} plays from {start_year} to {end_year}.")
    return pbp

# Function to load NFL ELO QB Rankings from CSV
def load_elo_qb_rankings(file_path):
    print(f"Loading ELO QB Rankings from {file_path}...")
    elo_data = pd.read_csv(file_path)
    print(f"Loaded {len(elo_data):,} rows from ELO QB Rankings.")
    return elo_data

# Function to scrape ESPN QBR rankings
def scrape_espn_qbr():
    url = "https://www.espn.com/nfl/qbr"
    print(f"Scraping QBR rankings from {url}...")
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to retrieve data from ESPN.")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    # Example: Parse table data (adjust selectors based on actual HTML structure)
    table = soup.find('table')
    if not table:
        print("No table found on ESPN QBR page.")
        return None

    df = pd.read_html(str(table))[0]
    print(f"Scraped {len(df):,} rows from ESPN QBR rankings.")
    return df

# Example usage
if __name__ == "__main__":
    # Load play-by-play data
    pbp_data = load_pbp_data(2010, 2025)

    # Load ELO QB Rankings
    elo_qb_rankings = load_elo_qb_rankings("data_load/nflELO_QB_RANKINGS.csv")

    # Scrape ESPN QBR rankings
    espn_qbr = scrape_espn_qbr()

    # Further cleaning and merging logic will go here