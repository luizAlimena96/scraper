import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.scraper import WebScraper
from app.ai_extractor import AIExtractor
from app.services import ScrapingService
from app.models import Company, AumSnapshot, ScrapeLog, Usage
from app.schemas import CompanyCreate


class TestWebScraper:
    @pytest.fixture
    def scraper(self):
        return WebScraper()
    
    def test_extract_relevant_chunks(self, scraper):
        html = """
        <html>
            <body>
                <p>Some irrelevant text here</p>
                <p>Our AUM is R$ 2.3 bilhões under management</p>
                <p>More irrelevant content</p>
                <div>Assets under management: US$ 1.5 billion</div>
            </body>
        </html>
        """
        
        result = scraper.extract_relevant_chunks(html)
        
        assert "AUM" in result or "Assets under management" in result
        assert "R$ 2.3" in result or "US$ 1.5" in result
    
    def test_should_use_playwright(self, scraper):
        assert scraper.should_use_playwright("https://instagram.com/company") == True
        assert scraper.should_use_playwright("https://twitter.com/company") == True
        assert scraper.should_use_playwright("https://example.com") == False
    
    @pytest.mark.asyncio
    async def test_scrape_url_requests(self, scraper):
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.text = "<html><body>Test content</body></html>"
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            content, status, error = await scraper.scrape_url("https://example.com")
            
            assert content == "<html><body>Test content</body></html>"
            assert status == 200
            assert error == ""


class TestAIExtractor:
    @pytest.fixture
    def ai_extractor(self):
        return AIExtractor()
    
    def test_parse_aum_response(self, ai_extractor):
        result = ai_extractor.parse_aum_response("R$ 2.3 BI", "https://example.com")
        assert result["aum_value"] == "$ 2.3 BI"
        assert result["aum_numeric"] == 2.3e9
        assert result["aum_unit"] == "bi"
        assert result["is_available"] == True
        
        result = ai_extractor.parse_aum_response("NAO_DISPONIVEL", "https://example.com")
        assert result["aum_value"] == "NAO_DISPONIVEL"
        assert result["is_available"] == False
    
    @pytest.mark.asyncio
    async def test_check_budget_and_run(self, ai_extractor):
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await ai_extractor.check_budget_and_run(mock_db)
        assert result == True


class TestScrapingService:
    @pytest.fixture
    def service(self):
        return ScrapingService()
    
    @pytest.fixture
    def mock_company(self):
        return Company(
            id=1,
            name="Test Company",
            url_site="https://example.com",
            url_linkedin="https://linkedin.com/company/test"
        )
    
    @pytest.mark.asyncio
    async def test_load_companies_from_csv(self, service):
        import tempfile
        import os
        
        csv_content = "name,url_site,url_linkedin\nTest Company,https://example.com,https://linkedin.com/test"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            mock_db = Mock()
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            companies = await service.load_companies_from_csv(csv_path, mock_db)
            
            assert len(companies) == 1
            assert companies[0].name == "Test Company"
            
        finally:
            os.unlink(csv_path)
    
    @pytest.mark.asyncio
    async def test_scrape_company(self, service, mock_company):
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        with patch('app.scraper.scraper.scrape_url') as mock_scrape:
            mock_scrape.return_value = ("<html>Test content with AUM R$ 1.5 bi</html>", 200, "")
            
            with patch('app.ai_extractor.ai_extractor.extract_aum') as mock_ai:
                mock_ai.return_value = {
                    "aum_value": "R$ 1.5 bi",
                    "aum_numeric": 1.5e9,
                    "aum_unit": "bi",
                    "confidence_score": 0.9,
                    "is_available": True,
                    "source_url": "https://example.com",
                    "source_type": "ai_extraction"
                }
                
                result = await service.scrape_company(mock_company, mock_db)
                
                assert result["company_id"] == 1
                assert result["company_name"] == "Test Company"
                assert len(result["scraped_urls"]) > 0
                assert result["aum_found"] == True


class TestModels:
    def test_company_model(self):
        company = Company(
            name="Test Company",
            url_site="https://example.com"
        )
        
        assert company.name == "Test Company"
        assert company.url_site == "https://example.com"
    
    def test_aum_snapshot_model(self):
        snapshot = AumSnapshot(
            company_id=1,
            aum_value="R$ 2.3 bi",
            aum_numeric=2.3e9,
            aum_unit="bi",
            source_url="https://example.com",
            confidence_score=0.9
        )
        
        assert snapshot.company_id == 1
        assert snapshot.aum_value == "R$ 2.3 bi"
        assert snapshot.aum_numeric == 2.3e9


class TestSchemas:
    def test_company_create_schema(self):
        company_data = {
            "name": "Test Company",
            "url_site": "https://example.com",
            "url_linkedin": "https://linkedin.com/test"
        }
        
        company = CompanyCreate(**company_data)
        
        assert company.name == "Test Company"
        assert company.url_site == "https://example.com"
        assert company.url_linkedin == "https://linkedin.com/test"


if __name__ == "__main__":
    pytest.main([__file__])
