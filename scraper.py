#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from loguru import logger
from retrying import retry

# Configure logger
logger.add("scraper.log", rotation="10 MB")

# Scraper Configuration
SEARCH_QUERY = "Python Developer"
LOCATION = "Москва"
PAGES_TO_SCRAPE = 5
OUTPUT_DIR = "data"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


class HHScraper:
    def __init__(self):
        self.base_url = "https://hh.ru"
        self.search_url = f"{self.base_url}/search/vacancy"
        self.jobs = []
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """Configure and return a Chrome WebDriver with anti-detection measures"""
        # Generate random user agent
        ua = UserAgent()
        user_agent = ua.random

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Setup Chrome service
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            # Fallback for Docker environment where ChromeDriverManager might not work
            logger.warning(f"Using default ChromeDriver path: {e}")
            driver = webdriver.Chrome(options=chrome_options)

        # Additional settings to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})

        return driver

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _wait_and_find_element(self, by, value, timeout=10):
        """Wait for an element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Element not found: {by}={value}")
            raise

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _wait_and_find_elements(self, by, value, timeout=10):
        """Wait for elements to be present and return them"""
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except TimeoutException:
            logger.error(f"Elements not found: {by}={value}")
            raise

    def _random_sleep(self, min_seconds=2, max_seconds=5):
        """Sleep for a random amount of time to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def search_jobs(self, query, location, pages=1):
        """Search for jobs with the given query and location"""
        logger.info(f"Searching for '{query}' in '{location}'")
        
        for page in range(pages):
            try:
                # Construct search URL with parameters
                url = f"{self.search_url}?text={query}&area={self._get_area_code(location)}&page={page}"
                logger.info(f"Navigating to page {page+1}: {url}")
                
                self.driver.get(url)
                self._random_sleep(3, 6)  # Longer wait for search page
                
                # Extract job listings
                self._extract_job_listings()
                
                logger.info(f"Completed page {page+1}, found {len(self.jobs)} jobs so far")
                
                # Random delay between pages
                if page < pages - 1:
                    self._random_sleep(5, 10)
                    
            except Exception as e:
                logger.error(f"Error processing page {page+1}: {str(e)}")
                continue

    def _get_area_code(self, location):
        """Map location name to HH.ru area code"""
        # Common area codes
        area_codes = {
            "Москва": "1",
            "Санкт-Петербург": "2",
            "Новосибирск": "4",
            "Екатеринбург": "3",
            "Казань": "88"
        }
        
        return area_codes.get(location, "1")  # Default to Moscow if not found

    def _extract_job_listings(self):
        """Extract job listings from the current page"""
        try:
            # Find all job listings
            job_elements = self._wait_and_find_elements(
                By.CSS_SELECTOR, ".vacancy-serp-item"
            )
            
            for job_element in job_elements:
                try:
                    # Extract job details
                    job_data = {}
                    
                    # Job title and URL
                    title_element = job_element.find_element(By.CSS_SELECTOR, ".serp-item__title")
                    job_data["title"] = title_element.text.strip()
                    job_data["url"] = title_element.get_attribute("href")
                    
                    # Company name
                    try:
                        job_data["company"] = job_element.find_element(
                            By.CSS_SELECTOR, ".bloko-link.bloko-link_kind-secondary"
                        ).text.strip()
                    except NoSuchElementException:
                        job_data["company"] = "Not specified"
                    
                    # Location
                    try:
                        job_data["location"] = job_element.find_element(
                            By.CSS_SELECTOR, "[data-qa='vacancy-serp__vacancy-address']"
                        ).text.strip()
                    except NoSuchElementException:
                        job_data["location"] = "Not specified"
                    
                    # Salary
                    try:
                        job_data["salary"] = job_element.find_element(
                            By.CSS_SELECTOR, "[data-qa='vacancy-serp__vacancy-compensation']"
                        ).text.strip()
                    except NoSuchElementException:
                        job_data["salary"] = "Not specified"
                    
                    # Description snippet
                    try:
                        job_data["description"] = job_element.find_element(
                            By.CSS_SELECTOR, ".vacancy-serp-item__meta-info-text"
                        ).text.strip()
                    except NoSuchElementException:
                        job_data["description"] = "Not specified"
                    
                    # Add timestamp
                    job_data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Add to jobs list
                    self.jobs.append(job_data)
                    
                except Exception as e:
                    logger.error(f"Error extracting job details: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding job listings: {str(e)}")

    def save_to_csv(self):
        """Save scraped jobs to a CSV file"""
        if not self.jobs:
            logger.warning("No jobs to save")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"hh_jobs_{timestamp}.csv")
        
        logger.info(f"Saving {len(self.jobs)} jobs to {filename}")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["title", "company", "location", "salary", 
                             "description", "url", "scraped_at"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for job in self.jobs:
                    writer.writerow(job)
                    
            logger.success(f"Successfully saved data to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")
            return None

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")


def main():
    """Main function to run the scraper"""
    logger.info("Starting HH.ru job scraper")
    
    try:
        # Initialize scraper
        scraper = HHScraper()
        
        # Search for jobs
        scraper.search_jobs(SEARCH_QUERY, LOCATION, PAGES_TO_SCRAPE)
        
        # Save results
        output_file = scraper.save_to_csv()
        
        if output_file:
            logger.info(f"Scraping completed. Results saved to {output_file}")
        else:
            logger.error("Failed to save results")
            
    except Exception as e:
        logger.error(f"Scraper failed: {str(e)}")
        
    finally:
        # Clean up
        if 'scraper' in locals():
            scraper.close()
        
        logger.info("Scraper finished")


if __name__ == "__main__":
    main()