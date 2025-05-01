#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import time
import random
from datetime import datetime
from typing import List, Dict, Optional, Union
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent
from loguru import logger
from retrying import retry

# Configuration
MAX_RETRIES = 3
DELAY_RANGE = (1, 5)  # Random delay in seconds
DDoS_TIMEOUT = 30  # Seconds to wait for DDoS protection

# Optimized selectors with multiple fallbacks
SELECTORS = {
    'job_card': [
        "div[class*='vacancy-serp-item']",
        "div[data-qa='vacancy-serp-vacancy']",
        "div[class*='vacancy-item']"
    ],
    'title': [
        "a[data-qa='serp-item__title']",
        "a.bloko-header-3",
        "a[class*='vacancy-title']"
    ],
    'company': [
        "a[data-qa='vacancy-serp__vacancy-employer']",
        "div[data-qa='vacancy-serp__vacancy-employer']",
        "span[class*='company-info-text']"
    ],
    'location': [
        "div[data-qa='vacancy-serp__vacancy-address']",
        "span[data-qa='vacancy-serp__vacancy-address']",
        "div.bloko-text_location"
    ],
    'salary': [
        "span[data-qa='vacancy-serp__vacancy-compensation']",
        "div[data-qa='vacancy-serp__vacancy-compensation']"
    ],
    'link': [
        "a[data-qa='vacancy-serp__vacancy-title']",
        "a[class*='serp-item__title']"
    ],
    'next_page': "a[data-qa='pager-next']",
    'ddos_guard': "title",
    'captcha': ".captcha__input"
}

class HHScraper:
    def __init__(self, headless=True):
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 20)
        self._setup_dirs()
    
    def _setup_dirs(self):
        """Create required directories"""
        os.makedirs("screenshots", exist_ok=True)
        os.makedirs("html_snapshots", exist_ok=True)
        os.makedirs("debug", exist_ok=True)
        os.makedirs("results", exist_ok=True)
    
    def _setup_driver(self, headless=True):
        """Configure Chrome with anti-detection measures"""
        chrome_options = Options()
        ua = UserAgent()
        
        # Basic configuration
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f"--window-size={random.randint(1200,1600)},{random.randint(800,1200)}")
        chrome_options.add_argument(f"user-agent={ua.random}")
        
        # Anti-detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Performance
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            self._apply_stealth_js(driver)
            return driver
        except Exception as e:
            logger.error(f"Driver initialization failed: {e}")
            raise
    
    def _apply_stealth_js(self, driver):
        """Execute JavaScript to mask automation"""
        scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            "window.navigator.chrome = {runtime: {}, etc: {}};"
        ]
        for script in scripts:
            driver.execute_script(script)
    
    def _human_like_interaction(self):
        """Simulate human behavior"""
        try:
            actions = ActionChains(self.driver)
            for _ in range(random.randint(2, 5)):
                actions.move_by_offset(random.randint(-100, 100), 
                                     random.randint(-100, 100))
            actions.perform()
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(200,800)})")
        except Exception as e:
            logger.debug(f"Human interaction failed: {e}")
    
    def _check_protection(self):
        """Check for DDoS-Guard or CAPTCHA"""
        try:
            if "DDoS-Guard" in self.driver.title:
                return "ddos"
            if self.driver.find_elements(By.CSS_SELECTOR, SELECTORS['captcha']):
                return "captcha"
            return None
        except:
            return None
    
    def _handle_protection(self, protection_type):
        """Handle protection mechanisms"""
        logger.warning(f"Detected {protection_type} protection")
        self.take_screenshot(f"{protection_type}_detected")
        return self._wait_for_ddos_guard() if protection_type == "ddos" else False
    
    def _wait_for_ddos_guard(self, timeout=DDoS_TIMEOUT):
        """Wait for DDoS protection to pass"""
        start = time.time()
        while time.time() - start < timeout:
            if not self._check_protection() == "ddos":
                return True
            time.sleep(2)
        return False
    
    def _find_element_text(self, parent, selectors: Union[str, List[str]]) -> str:
        """Find element text using multiple selectors"""
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
            except:
                continue
        return "Not specified"
    
    def _find_element_attr(self, parent, selectors: Union[str, List[str]], attr: str) -> Optional[str]:
        """Find element attribute using multiple selectors"""
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                return parent.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
            except:
                continue
        return None
    
    def _extract_job_listings(self) -> List[Dict[str, str]]:
        """Robust job extraction with validation"""
        self.save_html("current_page")
        jobs = []
        
        # Try all job card selectors
        for selector in SELECTORS['job_card']:
            try:
                job_cards = self._wait_and_find_elements(By.CSS_SELECTOR, selector)
                if job_cards:
                    logger.info(f"Found {len(job_cards)} jobs with selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector failed: {selector} - {e}")
        
        if not job_cards:
            logger.error("No job cards found")
            self._dump_page_structure()
            return []
        
        # Process each card
        for i, card in enumerate(job_cards):
            try:
                job = {
                    'title': self._find_element_text(card, SELECTORS['title']),
                    'company': self._find_element_text(card, SELECTORS['company']),
                    'location': self._find_element_text(card, SELECTORS['location']),
                    'salary': self._find_element_text(card, SELECTORS['salary']),
                    'link': self._find_element_attr(card, SELECTORS['link'], 'href'),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Validate required fields
                if job['title'] != "Not specified" and job['link']:
                    jobs.append(job)
                else:
                    logger.warning(f"Skipping invalid job card {i}")
                    
            except Exception as e:
                logger.error(f"Error processing card {i}: {e}")
                continue
        
        logger.info(f"Extracted {len(jobs)} valid jobs")
        return jobs
    
    def search_jobs(self, query: str, area_code: str = "113") -> List[Dict[str, str]]:
        """Main scraping workflow"""
        try:
            url = f"https://hh.ru/search/vacancy?text={query}&area={area_code}"
            self.driver.get(url)
            
            # Handle protection
            protection = self._check_protection()
            if protection and not self._handle_protection(protection):
                return []
            
            self._human_like_interaction()
            return self._process_pages()
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _process_pages(self) -> List[Dict[str, str]]:
        """Process multiple pages of results"""
        jobs = []
        page = 1
        
        while True:
            logger.info(f"Processing page {page}")
            page_jobs = self._extract_job_listings()
            jobs.extend(page_jobs)
            
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, SELECTORS['next_page'])
                next_btn.click()
                self.random_delay()
                page += 1
            except:
                break
                
        return jobs
    
    def save_to_csv(self, jobs: List[Dict[str, str]], filename: str = "jobs.csv"):
        """Save jobs to CSV with proper formatting"""
        if not jobs:
            logger.warning("No jobs to save")
            return
            
        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, 
                                      fieldnames=jobs[0].keys(),
                                      quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
                writer.writerows(jobs)
            logger.info(f"Saved {len(jobs)} jobs to {filename}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
    
    def random_delay(self):
        """Random delay between actions"""
        time.sleep(random.uniform(*DELAY_RANGE))
    
    def take_screenshot(self, name: str):
        """Save screenshot for debugging"""
        path = f"screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.driver.save_screenshot(path)
        logger.debug(f"Screenshot saved: {path}")
    
    def save_html(self, name: str):
        """Save page HTML for analysis"""
        path = f"html_snapshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        logger.debug(f"HTML saved: {path}")
    
    def _dump_page_structure(self):
        """Dump page structure for debugging"""
        debug_info = {
            "title": self.driver.title,
            "url": self.driver.current_url,
            "body_classes": self.driver.find_element(By.TAG_NAME, "body").get_attribute("class"),
            "div_classes": [div.get_attribute("class") for div in self.driver.find_elements(By.TAG_NAME, "div")]
        }
        path = f"debug/page_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(debug_info, f, indent=2)
        logger.error(f"Page structure dumped to {path}")

if __name__ == "__main__":
    logger.add("logs/scraper.log", rotation="1 day", retention="7 days")
    
    try:
        scraper = HHScraper()
        jobs = scraper.search_jobs("Грузчик", "113")  # 113 = Russia
        scraper.save_to_csv(jobs)
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
    finally:
        scraper.driver.quit()