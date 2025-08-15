# AUM Scraper

Aplicação para coleta automática de AUM (Assets Under Management) de empresas financeiras usando web scraping e IA.

## 🚀 Funcionalidades

- **Leitura de CSV**: Upload de arquivo CSV com empresas
- **Web Scraping**: Fetch de HTML público e conteúdo dinâmico usando Playwright
- **Extração via IA**: Uso do GPT-4o para extrair AUM com limite de 1500 tokens
- **Controle de Orçamento**: Monitoramento de custos da API OpenAI
- **Persistência**: Banco PostgreSQL com tabelas completas
- **Exportação**: Geração de arquivo Excel com resultados
- **API REST**: Endpoints para monitoramento e controle
- **Interface Web**: Dashboard para upload e monitoramento

## 🛠️ Stack Técnica

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0
- **Banco**: PostgreSQL 15
- **Scraping**: Playwright, BeautifulSoup4
- **IA**: OpenAI GPT-4o
- **Testes**: Pytest
- **Containerização**: Docker & Docker Compose

## 📋 Pré-requisitos

- Docker e Docker Compose
- Python 3.11+
- OpenAI API Key

## 🚀 Instalação

1. **Clone o repositório**:
```bash
git clone https://github.com/luizAlimena96/scraper.git
cd scraper
```

2. **Configure as variáveis de ambiente**:
```bash
cp .env.example .env
# Edite o arquivo .env com sua OpenAI API Key
```

3. **Execute com Docker**:
```bash
docker-compose up -d
```

4. **Acesse a aplicação**:
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📖 Uso

### 1. Upload de CSV
Faça upload do arquivo CSV com as empresas:
```bash
curl -X POST "http://localhost:8000/upload-csv" \
  -F "file=@companies_formatted.csv"
```

### 2. Iniciar Scraping
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"company_ids": null}'
```

### 3. Monitorar Progresso
```bash
curl "http://localhost:8000/scrape/status"
```

### 4. Exportar Resultados
```bash
curl "http://localhost:8000/export/excel" -o aum_results.xlsx
```

## 📁 Estrutura do Projeto

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── services.py          # Business logic
│   ├── scraper.py           # Web scraping
│   ├── ai_extractor.py      # AI extraction
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   └── static/              # Web dashboard
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker setup
├── Dockerfile              # Docker image
├── requirements.txt        # Dependencies
├── sample_companies.csv    # Example data
└── README.md              # Documentation
```

## 🔧 Características Técnicas

### Seleção Inteligente de Conteúdo
- `extract_relevant_chunks()`: Extrai parágrafos relevantes usando regex e keywords
- Limite de 1200 tokens antes do prompt
- Keywords: "AUM", "Assets under management", "patrimônio sob gestão"

### Controle de Crédito GPT
- `check_budget_and_run()`: Verifica orçamento diário
- Alerta quando > 80% do budget
- Bloqueia execuções quando budget excedido

### Reconciliação de Unidades
- Converte valores (mi, bi) para formato padronizado (ex.: 2.3e9)
- Suporte a R$, US$, bilhões, milhões

## 🧪 Testes

Execute os testes com cobertura:
```bash
docker exec scraper-backend-1 python -m pytest tests/ -v
```

## 📊 API Endpoints

### Empresas
- `POST /upload-csv` - Upload de CSV
- `GET /companies` - Listar empresas

### Scraping
- `POST /scrape` - Iniciar scraping
- `GET /scrape/status` - Status do scraping
- `POST /rescrape/{company_id}` - Re-scrape de empresa específica

### Resultados
- `GET /aum-snapshots` - Snapshots de AUM
- `GET /scrape-logs` - Logs de scraping
- `GET /export/excel` - Exportar para Excel

### Admin
- `GET /usage/today` - Consumo de tokens hoje

## 📈 Monitoramento

- **RabbitMQ UI**: http://localhost:15672
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000

## ⚠️ Observações Importantes

- Monitoramento de custos da API OpenAI
- Uso de prompt engineering e chunking inteligentes
- Registro de "NAO_DISPONIVEL" quando AUM não encontrado
- Rate limiting para evitar bloqueios
- Controle de paralelismo
