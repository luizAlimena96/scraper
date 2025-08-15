import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from typing import Tuple, Optional


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def should_use_playwright(self, url: str) -> bool:
        social_media_domains = ['instagram.com', 'twitter.com', 'x.com', 'facebook.com', 'linkedin.com']
        return any(domain in url.lower() for domain in social_media_domains)
    
    async def scrape_url(self, url: str, use_playwright: bool = False) -> Tuple[str, int, str]:
        try:
            if use_playwright:
                return await self._scrape_with_playwright(url)
            else:
                return await self._scrape_with_requests(url)
        except Exception as e:
            return "", 0, str(e)
    
    async def _scrape_with_requests(self, url: str) -> Tuple[str, int, str]:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, response.status_code, ""
        except Exception as e:
            return "", 0, str(e)
    
    async def _scrape_with_playwright(self, url: str) -> Tuple[str, int, str]:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle', timeout=30000)
                content = await page.content()
                await browser.close()
                return content, 200, ""
        except Exception as e:
            return "", 0, str(e)
    
    def extract_relevant_chunks(self, html: str, max_tokens: int = 1200) -> str:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text = soup.get_text()
            paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 10]
            
            aum_keywords = [
                'aum', 'assets under management', 'patrimônio sob gestão',
                'patrimonio sob gestao', 'gestão de ativos', 'gestao de ativos',
                'fundo', 'fundos', 'investimento', 'investimentos',
                'capital', 'ativo', 'ativos', 'portfólio', 'portfolio',
                'bilhões', 'bilhoes', 'milhões', 'milhoes', 'bi', 'mi', 'k', 'trilhões', 'trilhoes'
            ]
            currency_pattern = r'[R$US$€£¥]?\s*\d+[,.]?\d*\s*(?:bi|bilh[ãa]o|mi|milh[ãa]o|mil|k|milh[ãa]os|bilh[ãa]os|trilh[ãa]o|trilh[ãa]os|B|M|K|T)'
            
            relevant_chunks = []
            total_length = 0
            
            for paragraph in paragraphs:
                paragraph_lower = paragraph.lower()
                has_keywords = any(keyword in paragraph_lower for keyword in aum_keywords)
                has_currency = re.search(currency_pattern, paragraph, re.IGNORECASE)
                
                if has_keywords or has_currency:
                    chunk_length = len(paragraph)
                    if total_length + chunk_length <= max_tokens * 4:
                        relevant_chunks.append(paragraph)
                        total_length += chunk_length
                    else:
                        break
            
            if not relevant_chunks:
                for paragraph in paragraphs[:5]:
                    chunk_length = len(paragraph)
                    if total_length + chunk_length <= max_tokens * 4:
                        relevant_chunks.append(paragraph)
                        total_length += chunk_length
                    else:
                        break
            
            return '\n\n'.join(relevant_chunks)
        except Exception as e:
            return html[:max_tokens * 4]


scraper = WebScraper()
