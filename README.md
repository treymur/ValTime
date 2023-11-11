
# Chapter Printer for Valorant

ValTime is a Python application that retrieves and displays round timestamps for Valorant VODs. It uses the henrikdev.xyz Valorant API to fetch player data based on Riot ID and Match ID inputs.

## Features

- Fetch match details using Match ID.
- Display match timelines.
- Copy round times to clipboard for easy sharing.

## Installation

To run Chapter Printer, you'll need Python installed on your system. The application is developed with Python 3.11, but it should be compatible with newer versions as well. Follow these steps to set up the application:

1. Clone the repository to your local machine:

   ```bash
   git clone https://your-repository-url.git
   cd path-to-cloned-repo
   ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Run the application:

    ```bash
    python gui.py
    ```

## Usage

Upon launching Chapter Printer, you will be prompted to enter your Riot ID and Match ID. After inputting the required information, the application will fetch and display the match round times.

- **Riot ID**: Enter your Valorant Riot ID in the format `username#TAG`.
- **Match ID**: Enter the specific match ID you wish to get statistics for. You can find the match ID by finding the desired match on [tracker.gg](https://tracker.gg/valorant/), opening the match in a new tab, and look at the last part of the URL (text after /valorant/match/)
- **Start Time**: Enter the exact time of the end of the first pre-round. Can be in `h:mm:ss`, `m:ss`, or `sss` format.

If the entered information is correct, you will be presented with the round times relative to the VOD including round kill and clutch stats, which you can copy to your clipboard.

---

Created by Trenton Murray