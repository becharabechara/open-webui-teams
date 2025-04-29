"""
title: Web Search using Bing and Scrape first N Pages
author: velepost (updated by Grok)
funding_url: https://github.com/open-webui
version: 0.1.13
license: MIT
"""

import os
import requests
from datetime import datetime
import json
from bs4 import BeautifulSoup
import concurrent.futures
import unicodedata
import re
import asyncio
from typing import Callable, Any, Optional
from pydantic import BaseModel, Field
from urllib.parse import urlparse
import validators
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]

def get_filtered_results(results, filter_list):
    if not filter_list:
        return results
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        if not validators.url(url):
            continue
        domain = urlparse(url).netloc
        if any(domain.endswith(filtered_domain) for filtered_domain in filter_list):
            filtered_results.append(result)
    return filtered_results

class HelpFunctions:
    def __init__(self):
        pass

    def get_base_url(self, url):
        parsed_url = urlparse(url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    def generate_excerpt(self, content, max_length=200):
        return content[:max_length] + "..." if len(content) > max_length else content

    def format_text(self, original_text, max_words):
        """Clean and summarize text, strictly limiting to max_words."""
        soup = BeautifulSoup(original_text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = self.remove_emojis(text)
        boilerplate = r"(Skip to main content|Home|Contact|Login|Sign up|Footer|©.*?$|\b\d{4}\b.*rights reserved|%PDF-\d+\.\d+|obj\s*<<|>>|endobj|JavaScript n'est pas activÃ|Comment activer le JavaScript)"
        text = re.sub(boilerplate, "", text, flags=re.IGNORECASE)
        words = text.split()
        return " ".join(words[:max_words])

    def remove_emojis(self, text):
        return "".join(c for c in text if not unicodedata.category(c).startswith("So"))

    def process_search_result(self, result, valves):
        title_site = self.remove_emojis(result["name"])
        url_site = result["url"]
        snippet = result.get("snippet", "")

        if valves.IGNORED_WEBSITES:
            base_url = self.get_base_url(url_site)
            ignored_sites = [site.strip() for site in valves.IGNORED_WEBSITES.split(",")]
            if any(ignored_site in base_url for ignored_site in ignored_sites):
                logger.debug(f"Skipping {url_site} - matches ignored website")
                return None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
            }
            response_site = requests.get(url_site, timeout=20, headers=headers)
            response_site.raise_for_status()
            html_content = response_site.text
            content_site = self.format_text(html_content, valves.PAGE_CONTENT_WORDS_LIMIT)
            return {
                "link": url_site,
                "title": title_site,
                "snippet": self.remove_emojis(snippet[:200]),
                "content": content_site
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url_site}: {str(e)}")
            return None

class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None):
        self.event_emitter = event_emitter

    async def emit(self, description="Unknown State", status="in_progress", done=False):
        if self.event_emitter:
            await self.event_emitter({
                "type": "status",
                "data": {"status": status, "description": description, "done": done},
            })

class Tools:
    class Valves(BaseModel):
        BING_API_ENDPOINT: str = Field(
            default="https://api.bing.microsoft.com/v7.0/search",
            description="The endpoint for Bing Search API"
        )
        BING_API_KEY: str = Field(
            default=os.getenv("BING_API_KEY", "YOUR_BING_API_KEY"),
            description="Your Bing Search API key"
        )
        IGNORED_WEBSITES: str = Field(
            default="",
            description="Comma-separated list of websites to ignore"
        )
        INCLUDED_DOMAINS: str = Field(
            default="",
            description="Comma-separated list of domains to include (optional positive filter)"
        )
        RETURNED_SCRAPPED_PAGES_NO: int = Field(
            default=3,
            description="The number of Search Engine Results to Parse"
        )
        SCRAPPED_PAGES_NO: int = Field(
            default=6,
            description="Total pages scraped. Ideally greater than returned pages"
        )
        PAGE_CONTENT_WORDS_LIMIT: int = Field(
            default=5000,
            description="Limit words content for each page"
        )
        CITATION_LINKS: bool = Field(
            default=True,
            description="If True, send custom citations with links"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def search_web(self, query: str, __event_emitter__: Callable[[dict], Any] = None) -> str:
        functions = HelpFunctions()
        emitter = EventEmitter(__event_emitter__)

        await emitter.emit(f"Initiating web search for: {query}")
        search_engine_url = self.valves.BING_API_ENDPOINT

        if self.valves.RETURNED_SCRAPPED_PAGES_NO > self.valves.SCRAPPED_PAGES_NO:
            self.valves.RETURNED_SCRAPPED_PAGES_NO = self.valves.SCRAPPED_PAGES_NO

        params = {"q": query, "count": self.valves.SCRAPPED_PAGES_NO}
        headers = {"Ocp-Apim-Subscription-Key": self.valves.BING_API_KEY}

        try:
            await emitter.emit("Sending request to Bing Search API")
            resp = requests.get(search_engine_url, params=params, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            raw_results = data.get("webPages", {}).get("value", [])
            included_domains = [d.strip() for d in self.valves.INCLUDED_DOMAINS.split(",")] if self.valves.INCLUDED_DOMAINS else None
            filtered_results = get_filtered_results(raw_results, included_domains) if included_domains else raw_results
            results = filtered_results[:self.valves.RETURNED_SCRAPPED_PAGES_NO]
            await emitter.emit(f"Retrieved {len(results)} filtered search results")
        except requests.exceptions.RequestException as e:
            error_details = {"error": str(e), "query": query}
            logger.error(f"Search error: {json.dumps(error_details, indent=2)}")
            await emitter.emit(status="error", description=f"Error during search: {str(e)}", done=True)
            return json.dumps(error_details)

        results_json = []
        if results:
            await emitter.emit(f"Processing search results")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(functions.process_search_result, result, self.valves) for result in results]
                for future in concurrent.futures.as_completed(futures):
                    result_json = future.result()
                    if result_json:
                        try:
                            json.dumps(result_json)
                            results_json.append(result_json)
                        except (TypeError, ValueError) as e:
                            logger.error(f"Skipping invalid result due to {str(e)}")
                            continue
                    if len(results_json) >= self.valves.RETURNED_SCRAPPED_PAGES_NO:
                        break

        if self.valves.CITATION_LINKS and __event_emitter__:
            for idx, result in enumerate(results_json):
                citation = {
                    "type": "citation",
                    "data": {
                        "document": [result["content"]],
                        "metadata": [{"source": result["link"]}],
                        "source": {"name": result["title"], "id": str(idx)},
                    },
                }
                await __event_emitter__(citation)

        await emitter.emit(
            status="complete",
            description=f"Web search completed. Retrieved content from {len(results_json)} pages",
            done=True,
        )
        final_results = [SearchResult(**{k: v for k, v in r.items() if k in ["link", "title", "snippet"]}).dict() | {"content": r["content"]} for r in results_json]
        return json.dumps(final_results, ensure_ascii=False)

    async def get_website(self, url: str, __event_emitter__: Callable[[dict], Any] = None) -> str:
        if not validators.url(url):
            return json.dumps([{"link": url, "title": None, "snippet": None, "content": "Invalid URL provided"}])

        functions = HelpFunctions()
        emitter = EventEmitter(__event_emitter__)

        await emitter.emit(f"Fetching content from URL: {url}")
        results_json = []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
            }
            response_site = requests.get(url, headers=headers, timeout=120)
            response_site.raise_for_status()
            html_content = response_site.text
            await emitter.emit("Parsing website content")
            content_site = functions.format_text(html_content, self.valves.PAGE_CONTENT_WORDS_LIMIT)
            result_site = {
                "link": url,
                "title": BeautifulSoup(html_content, "html.parser").title.string or "No title found",
                "snippet": functions.generate_excerpt(content_site),
                "content": content_site,
            }
            results_json.append(result_site)
            if self.valves.CITATION_LINKS and __event_emitter__:
                citation = {
                    "type": "citation",
                    "data": {
                        "document": [result_site["content"]],
                        "metadata": [{"source": url}],
                        "source": {"name": result_site["title"], "id": "0"},
                    },
                }
                await __event_emitter__(citation)
            await emitter.emit(status="complete", description="Website content retrieved and processed successfully", done=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching website {url}: {str(e)}")
            results_json.append({"link": url, "title": None, "snippet": None, "content": f"Failed to retrieve the page. Error: {str(e)}"})
            await emitter.emit(status="error", description=f"Error fetching website content: {str(e)}", done=True)

        return json.dumps([SearchResult(**{k: v for k, v in r.items() if k in ["link", "title", "snippet"]}).dict() | {"content": r["content"]} for r in results_json], ensure_ascii=False)