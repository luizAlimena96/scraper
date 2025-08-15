import asyncio
import re
import openai
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Usage
from datetime import datetime, date

openai.api_key = settings.openai_api_key

class AIExtractor:
    def __init__(self):
        self.daily_budget = settings.daily_budget_usd
        self.max_tokens = settings.max_tokens_per_request
    
    async def check_budget_and_run(self, db: Session) -> bool:
        today = date.today()
        usage = db.query(Usage).filter(Usage.date >= today).first()
        
        if usage and usage.cost_usd >= self.daily_budget * 0.8:
            return False
        
        return True
    
    async def extract_aum(self, company_name: str, content: str, source_url: str, db: Session) -> dict:
        if not await self.check_budget_and_run(db):
            return {
                "aum_value": "NAO_DISPONIVEL",
                "aum_numeric": None,
                "aum_unit": None,
                "confidence_score": 0.0,
                "is_available": False,
                "source_url": source_url,
                "source_type": "ai_extraction"
            }
        
        prompt = f"Qual é o patrimônio sob gestão (AUM) anunciado por {company_name}? Responda somente com o número e a unidade (ex.: R$ 2,3 bi) ou NAO_DISPONIVEL.\n\nConteúdo da fonte: {content[:1000]}"
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em extrair informações financeiras de textos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            ai_response = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            await self._log_usage(db, tokens_used)
            
            return self.parse_aum_response(ai_response, source_url)
            
        except Exception as e:
            return {
                "aum_value": "NAO_DISPONIVEL",
                "aum_numeric": None,
                "aum_unit": None,
                "confidence_score": 0.0,
                "is_available": False,
                "source_url": source_url,
                "source_type": "ai_extraction"
            }
    
    def parse_aum_response(self, response: str, source_url: str) -> dict:
        if "NAO_DISPONIVEL" in response.upper():
            return {
                "aum_value": "NAO_DISPONIVEL",
                "aum_numeric": None,
                "aum_unit": None,
                "confidence_score": 0.0,
                "is_available": False,
                "source_url": source_url,
                "source_type": "ai_extraction"
            }
        
        currency_pattern = r'([R$US$€£¥]?)\s*(\d+[,.]?\d*)\s*(bi|bilh[ãa]o|mi|milh[ãa]o|mil|k|milh[ãa]os|bilh[ãa]os|trilh[ãa]o|trilh[ãa]os|B|M|K|T)'
        match = re.search(currency_pattern, response, re.IGNORECASE)
        
        if not match:
            return {
                "aum_value": "NAO_DISPONIVEL",
                "aum_numeric": None,
                "aum_unit": None,
                "confidence_score": 0.0,
                "is_available": False,
                "source_url": source_url,
                "source_type": "ai_extraction"
            }
        
        currency = match.group(1) or "$"
        value = float(match.group(2).replace(',', '.'))
        unit = match.group(3).lower()
        
        numeric_value = self._convert_to_numeric(value, unit)
        
        return {
            "aum_value": f"{currency} {value} {unit.upper()}",
            "aum_numeric": numeric_value,
            "aum_unit": unit,
            "confidence_score": 0.9,
            "is_available": True,
            "source_url": source_url,
            "source_type": "ai_extraction"
        }
    
    def _convert_to_numeric(self, value: float, unit: str) -> float:
        unit_mapping = {
            'k': 1e3,
            'mil': 1e3,
            'mi': 1e6,
            'milhão': 1e6,
            'milhao': 1e6,
            'milhões': 1e6,
            'milhoes': 1e6,
            'm': 1e6,
            'bi': 1e9,
            'bilhão': 1e9,
            'bilhao': 1e9,
            'bilhões': 1e9,
            'bilhoes': 1e9,
            'b': 1e9,
            'trilhão': 1e12,
            'trilhao': 1e12,
            'trilhões': 1e12,
            'trilhoes': 1e12,
            't': 1e12
        }
        
        multiplier = unit_mapping.get(unit, 1)
        return value * multiplier
    
    async def _log_usage(self, db: Session, tokens: int):
        today = date.today()
        usage = db.query(Usage).filter(Usage.date >= today).first()
        
        if usage:
            usage.total_tokens += tokens
            usage.requests_count += 1
            usage.cost_usd = (usage.total_tokens / 1000) * 0.01
        else:
            usage = Usage(
                date=datetime.utcnow(),
                total_tokens=tokens,
                requests_count=1,
                cost_usd=(tokens / 1000) * 0.01
            )
            db.add(usage)
        
        db.commit()


ai_extractor = AIExtractor()
