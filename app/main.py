from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from app.database import engine, get_db
from app.models import Base, Company, AumSnapshot, ScrapeLog, Usage
from app.schemas import Company as CompanySchema, AumSnapshot as AumSnapshotSchema, ScrapeLog as ScrapeLogSchema, Usage as UsageSchema, ScrapeRequest, ScrapeResponse
from app.services import scraping_service

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AUM Scraper API", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    file_path = f"data/{file.filename}"
    os.makedirs("data", exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        companies = await scraping_service.load_companies_from_csv(file_path, db)
        return {"message": f"Successfully loaded {len(companies)} companies", "companies": companies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies", response_model=List[CompanySchema])
async def get_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    return companies

@app.post("/scrape", response_model=ScrapeResponse)
async def start_scraping(request: ScrapeRequest, db: Session = Depends(get_db)):
    try:
        result = await scraping_service.scrape_companies(request.company_ids, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scrape/status")
async def get_scrape_status(db: Session = Depends(get_db)):
    total_companies = db.query(Company).count()
    companies_with_aum = db.query(AumSnapshot).distinct(AumSnapshot.company_id).count()
    total_scrapes = db.query(ScrapeLog).count()
    successful_scrapes = db.query(ScrapeLog).filter(ScrapeLog.status == "success").count()
    
    success_rate = (successful_scrapes / total_scrapes * 100) if total_scrapes > 0 else 0
    
    return {
        "total_companies": total_companies,
        "companies_with_aum": companies_with_aum,
        "total_scrapes": total_scrapes,
        "successful_scrapes": successful_scrapes,
        "success_rate": round(success_rate, 1)
    }

@app.get("/aum-snapshots", response_model=List[AumSnapshotSchema])
async def get_aum_snapshots(db: Session = Depends(get_db)):
    snapshots = db.query(AumSnapshot).order_by(AumSnapshot.created_at.desc()).all()
    return snapshots

@app.get("/scrape-logs", response_model=List[ScrapeLogSchema])
async def get_scrape_logs(db: Session = Depends(get_db)):
    logs = db.query(ScrapeLog).order_by(ScrapeLog.created_at.desc()).limit(100).all()
    return logs

@app.get("/usage/today", response_model=UsageSchema)
async def get_today_usage(db: Session = Depends(get_db)):
    from datetime import date
    today = date.today()
    usage = db.query(Usage).filter(Usage.date >= today).first()
    
    if not usage:
        usage = Usage(
            date=today,
            total_tokens=0,
            cost_usd=0.0,
            requests_count=0
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    
    return usage

@app.get("/export/excel")
async def export_excel(db: Session = Depends(get_db)):
    try:
        output_path = scraping_service.export_to_excel(db)
        return FileResponse(
            path=output_path,
            filename="aum_results.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting to Excel: {e}")

@app.post("/rescrape/{company_id}")
async def rescrape_company(company_id: int, db: Session = Depends(get_db)):
    try:
        result = await scraping_service.scrape_companies([company_id], db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
