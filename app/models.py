from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url_site = Column(String, nullable=True)
    url_linkedin = Column(String, nullable=True)
    url_instagram = Column(String, nullable=True)
    url_x = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    aum_snapshots = relationship("AumSnapshot", back_populates="company")
    scrape_logs = relationship("ScrapeLog", back_populates="company")

class ScrapeLog(Base):
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    content_length = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="scrape_logs")

class AumSnapshot(Base):
    __tablename__ = "aum_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    aum_value = Column(String, nullable=False)
    aum_numeric = Column(Float, nullable=True)
    aum_unit = Column(String, nullable=True)
    source_url = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    confidence_score = Column(Float, default=0.0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="aum_snapshots")

class Usage(Base):
    __tablename__ = "usage"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    requests_count = Column(Integer, default=0)
