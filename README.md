# HH.ru Job Scraper

A Docker-based web scraper for extracting job listings from hh.ru (HeadHunter) using Python and Selenium with headless Chrome.

## Features

- Scrapes job listings from hh.ru based on search criteria
- Runs in a containerized environment for easy deployment
- Uses headless Chrome browser to avoid detection
- Extracts job titles, companies, salaries, and other relevant information
- Exports data to CSV format

## Requirements

- Docker
- Docker Compose (optional, for easier management)

## Setup

1. Clone this repository
2. Build the Docker image:
   ```
   docker build -t hh-scraper .
   ```
3. Run the container:
   ```
   docker run -v $(pwd)/data:/app/data hh-scraper
   ```

## Usage

By default, the scraper will search for jobs based on the parameters in the script. You can modify the search parameters by editing the `scraper.py` file.

### Configuration Options

Edit the following variables in `scraper.py` to customize your search:

- `SEARCH_QUERY`: The job title or keywords to search for
- `LOCATION`: The city or region to search in
- `PAGES_TO_SCRAPE`: Number of pages to scrape

### Output

The scraped data will be saved to the `data` directory in CSV format with a timestamp in the filename.

## Legal Disclaimer

This tool is for educational purposes only. Web scraping may be against the terms of service of some websites. Use responsibly and at your own risk.

## License

MIT