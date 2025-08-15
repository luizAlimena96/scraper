import asyncio
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Company, ScrapeLog, AumSnapshot
from app.scraper import scraper
from app.ai_extractor import ai_extractor
from app.schemas import CompanyCreate, AumSnapshotCreate, ScrapeLogCreate


class ScrapingService:
    def __init__(self):
        self.max_concurrent_requests = 3
    
    async def load_companies_from_csv(self, csv_path: str, db: Session) -> List[Company]:
        try:
            df = pd.read_csv(csv_path)
            companies = []
            
            for _, row in df.iterrows():
                company_data = CompanyCreate(
                    name=row['name'],
                    url_site=row.get('url_site') if pd.notna(row.get('url_site')) else None,
                    url_linkedin=row.get('url_linkedin') if pd.notna(row.get('url_linkedin')) else None,
                    url_instagram=row.get('url_instagram') if pd.notna(row.get('url_instagram')) else None,
                    url_x=row.get('url_x') if pd.notna(row.get('url_x')) else None
                )
                
                company = Company(**company_data.dict())
                db.add(company)
                companies.append(company)
            
            db.commit()
            
            for company in companies:
                db.refresh(company)
            
            return companies
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Error loading companies from CSV: {e}")
    
    async def scrape_company(self, company: Company, db: Session) -> Dict[str, Any]:
        results = {
            "company_id": company.id,
            "company_name": company.name,
            "scraped_urls": [],
            "aum_found": False,
            "aum_snapshots": []
        }
        
        urls_to_scrape = []
        if company.url_site:
            urls_to_scrape.append(("website", company.url_site))
        if company.url_linkedin:
            urls_to_scrape.append(("linkedin", company.url_linkedin))
        if company.url_instagram:
            urls_to_scrape.append(("instagram", company.url_instagram))
        if company.url_x:
            urls_to_scrape.append(("x", company.url_x))
        
        for source_type, url in urls_to_scrape:
            try:
                use_playwright = scraper.should_use_playwright(url)
                content, status_code, error_message = await scraper.scrape_url(url, use_playwright)
                
                scrape_log = ScrapeLogCreate(
                    company_id=company.id,
                    url=url,
                    status="success" if status_code == 200 else "failed",
                    content_length=len(content) if content else 0,
                    error_message=error_message
                )
                
                db.add(ScrapeLog(**scrape_log.dict()))
                db.commit()
                
                results["scraped_urls"].append({
                    "url": url,
                    "status": "success" if status_code == 200 else "failed",
                    "content_length": len(content) if content else 0
                })
                
                if status_code == 200 and content:
                    relevant_content = scraper.extract_relevant_chunks(content)
                    
                    if relevant_content:
                        aum_info = await ai_extractor.extract_aum(
                            company.name, 
                            relevant_content, 
                            url, 
                            db
                        )
                        
                        if aum_info["is_available"] and aum_info["aum_value"] != "NAO_DISPONIVEL":
                            aum_snapshot = AumSnapshotCreate(
                                company_id=company.id,
                                aum_value=aum_info["aum_value"],
                                aum_numeric=aum_info["aum_numeric"],
                                aum_unit=aum_info["aum_unit"],
                                source_url=url,
                                source_type=source_type,
                                confidence_score=aum_info["confidence_score"],
                                is_available=True
                            )
                            
                            db.add(AumSnapshot(**aum_snapshot.dict()))
                            db.commit()
                            
                            results["aum_snapshots"].append(aum_info)
                            results["aum_found"] = True
                
                await asyncio.sleep(1)
                
            except Exception as e:
                scrape_log = ScrapeLogCreate(
                    company_id=company.id,
                    url=url,
                    status="failed",
                    error_message=str(e)
                )
                db.add(ScrapeLog(**scrape_log.dict()))
                db.commit()
                
                results["scraped_urls"].append({
                    "url": url,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    async def scrape_companies(self, company_ids: Optional[List[int]] = None, db: Session = None) -> Dict[str, Any]:
        if not db:
            from app.database import SessionLocal
            db = SessionLocal()
        
        try:
            if company_ids:
                companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
            else:
                companies = db.query(Company).all()
            
            if not companies:
                return {
                    "message": "No companies found to scrape",
                    "companies_processed": 0,
                    "successful_scrapes": 0,
                    "failed_scrapes": 0
                }
            
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def scrape_with_semaphore(company):
                async with semaphore:
                    return await self.scrape_company(company, db)
            
            tasks = [scrape_with_semaphore(company) for company in companies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_scrapes = 0
            failed_scrapes = 0
            
            for result in results:
                if isinstance(result, Exception):
                    failed_scrapes += 1
                elif result.get("aum_found"):
                    successful_scrapes += 1
                else:
                    failed_scrapes += 1
            
            return {
                "message": f"Scraping completed for {len(companies)} companies",
                "companies_processed": len(companies),
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": failed_scrapes,
                "results": results
            }
            
        except Exception as e:
            raise Exception(f"Error in scraping companies: {e}")
        finally:
            if db:
                db.close()
    
    def export_to_excel(self, db: Session, output_path: str = "aum_results.xlsx"):
        try:
            companies = db.query(Company).all()
            
            data = []
            for company in companies:
                latest_aum = db.query(AumSnapshot).filter(
                    AumSnapshot.company_id == company.id
                ).order_by(AumSnapshot.created_at.desc()).first()
                
                data.append({
                    "Company Name": company.name,
                    "Website": company.url_site or "",
                    "LinkedIn": company.url_linkedin or "",
                    "Instagram": company.url_instagram or "",
                    "X (Twitter)": company.url_x or "",
                    "AUM Value": latest_aum.aum_value if latest_aum else "NAO_DISPONIVEL",
                    "AUM Numeric": latest_aum.aum_numeric if latest_aum else None,
                    "AUM Unit": latest_aum.aum_unit if latest_aum else None,
                    "Source URL": latest_aum.source_url if latest_aum else "",
                    "Source Type": latest_aum.source_type if latest_aum else "",
                    "Confidence Score": latest_aum.confidence_score if latest_aum else 0.0,
                    "Last Updated": latest_aum.created_at.replace(tzinfo=None) if latest_aum else "",
                })
            
            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Error exporting to Excel: {e}")


scraping_service = ScrapingService()
