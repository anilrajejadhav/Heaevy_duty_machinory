# TVH Findability Demo

A deliberately small, local application for the TVH technical case. It helps a
user find a label, decal, or part reference from a free-text description and
then suggests articles frequently bought in the same order.

## Why this approach

The demo uses TF-IDF search instead of a large language model. It runs on a
normal CPU-only laptop, gives repeatable results, and is easy to explain in a
15-minute interview. A production version can replace `CatalogSearch` with a
hybrid vector and keyword engine without changing the API.

## Architecture

```text
PDF/TXT/CSV catalogue -> text extraction -> TF-IDF index -> /search
Purchase-history CSV -> article-pair counts -> /recommendations/{reference}
```

## Setup

Use Python 3.11 or newer in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to use the interactive API page.

## Demo flow

1. Index the label catalogue (use a small page count first if the PDF is large):

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/ingest `
  -ContentType 'application/json' `
  -Body '{"paths":["12594102_Labels_Decals.pdf"],"replace_index":true}'
```

2. Search using a customer-style description:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/search `
  -ContentType 'application/json' `
  -Body '{"query":"warning decal for forklift battery"}'
```

3. Build recommendations from the supplied dummy data:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/recommendations/build `
  -ContentType 'application/json' `
  -Body '{"csv_path":"dummy_purchases.csv"}'
```

4. Ask for recommendations after selecting a product reference:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/recommendations/REF%20111TA2234
```

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check readiness and counts. |
| `POST /ingest` | Extract and index PDF, TXT, or CSV catalogue sources. |
| `POST /search` | Search from free text and return source page plus excerpt. |
| `POST /recommendations/build` | Aggregate frequently-bought-together pairs. |
| `GET /recommendations/{reference_number}` | Return the top related articles. |

## Evaluation

`app/evaluation/metrics.py` includes Precision@K, Recall@K, Hit Rate@K, and
MRR. Before presenting, prepare 10-20 realistic customer descriptions, label
the expected catalogue page or reference number, and use these metrics to show
how accurately the search works.

## Production path

For a full TVH deployment, run ingestion asynchronously, store products in a
product-information database, combine exact reference matching with vector
search, add user feedback/relevance metrics, and serve recommendations from a
scheduled batch pipeline. The public API contract can remain the same.
