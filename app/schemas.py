from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    url_site: Optional[str] = None
    url_linkedin: Optional[str] = None
    url_instagram: Optional[str] = None
    url_x: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AumSnapshotBase(BaseModel):
    company_id: int
    aum_value: str
    aum_numeric: Optional[float] = None
    aum_unit: Optional[str] = None
    source_url: str
    source_type: str
    confidence_score: float = 0.0
    is_available: bool = True

class AumSnapshotCreate(AumSnapshotBase):
    pass

class AumSnapshot(AumSnapshotBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScrapeLogBase(BaseModel):
    company_id: int
    url: str
    status: str
    content_length: int = 0
    error_message: Optional[str] = None

class ScrapeLogCreate(ScrapeLogBase):
    pass

class ScrapeLog(ScrapeLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class UsageBase(BaseModel):
    date: datetime
    total_tokens: int = 0
    cost_usd: float = 0.0
    requests_count: int = 0

class Usage(UsageBase):
    id: int
    
    class Config:
        from_attributes = True

class ScrapeRequest(BaseModel):
    company_ids: Optional[List[int]] = None

class ScrapeResponse(BaseModel):
    message: str
    companies_processed: int
    successful_scrapes: int
    failed_scrapes: int
    results: Optional[List[dict]] = None

class CompanyResult(BaseModel):
    company_id: int
    company_name: str
    scraped_urls: List[dict]
    aum_found: bool
    aum_snapshots: List[dict]
