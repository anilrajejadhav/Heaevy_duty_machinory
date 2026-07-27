# TVH Findability Demo

A small, local FastAPI application for the TVH technical recruitment case.
It lets a user describe a label, decal, or part in plain language, finds the
most relevant catalogue pages, and then suggests articles that are frequently
purchased together.

The project is intentionally simple: it runs on a normal CPU-only laptop and
does not need an LLM, API key, GPU, or cloud account.

## What the demo does

1. Reads product catalogues from PDF, TXT, or CSV files.
2. Extracts text while retaining the source file and PDF page number.
3. Builds a local TF-IDF search index.
4. Searches using natural-language product descriptions.
5. Reads purchase history and counts which references appear together.
6. Exposes all functionality through a FastAPI REST API.

## Why TF-IDF instead of an LLM?

TF-IDF is a good demonstration choice for this exercise because it is:

- Fast and inexpensive to run locally.
- Easy to explain in an interview.
- Deterministic: the same query gives the same ranking.
- Useful as a baseline before introducing vector search or an LLM.

For production, this search layer can be upgraded to hybrid keyword + vector
search while preserving the REST API.

## Architecture

```text
                        +--------------------+
PDF / TXT / CSV ------> | Text extraction    |
                        +--------------------+
                                  |
                                  v
                        +--------------------+
User description -----> | TF-IDF search      | -----> Source page, excerpt,
                        +--------------------+        reference numbers

Purchase history CSV --> Pair-count algorithm -------> Related article references
```

## Project structure

```text
app/
  api/routes.py                 # FastAPI endpoints
  ingestion/loader.py           # PDF, TXT, and CSV text extraction
  retrieval/search.py           # TF-IDF index and ranked search
  recommendations/service.py    # Frequently-bought-together logic
  evaluation/metrics.py         # Precision@K, Recall@K, Hit Rate, MRR
  utils/config.py               # Environment settings and local paths
  main.py                       # FastAPI application entry point
data/                           # Optional local input and generated data
models/                         # Generated search and recommendation JSON files
tests/                          # Unit tests
requirements.txt                # Python dependencies
```

## Prerequisites

- Windows, macOS, or Linux
- Python 3.11 or newer
- PowerShell terminal (commands below use PowerShell)

Check Python:

```powershell
python --version
```

## Step 1: Open the project

Open the folder in VS Code:

```text
E:\Heaevy_duty_machinory
```

Open a VS Code terminal in that folder.

## Step 2: Create and activate a virtual environment

If you do not already have a virtual environment, create one:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, your terminal should begin with `(.venv)`.

> If you are already using the existing `henv` environment, activate it with
> ` .\henv\Scripts\Activate.ps1` instead.

## Step 3: Install dependencies

Install all packages listed in `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Verify the installation:

```powershell
python -m pytest -q
```

Expected result: all tests pass.

## Step 4: Optional configuration

The default configuration works without changes. To customize it, copy the
example environment file:

```powershell
Copy-Item .env.example .env
```

For a faster initial PDF demonstration, open `.env` and set:

```env
MAX_PAGES_PER_PDF=30
```

Use `MAX_PAGES_PER_PDF=0` to index every page. Indexing every page takes longer
on a low-configuration laptop, especially for a large catalogue.

## Step 5: Start FastAPI

Run the application from the project root:

```powershell
uvicorn app.main:app --reload
```

Expected output includes a local address similar to:

```text
Uvicorn running on http://127.0.0.1:8000
```

Leave this terminal running while testing. Open the interactive Swagger page:

```text
http://127.0.0.1:8000/docs
```

## Step 6: Test the health endpoint

Open a second terminal and run:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

Before indexing, a typical response is:

```json
{
  "status": "ok",
  "indexed_items": 0,
  "recommendation_articles": 0
}
```

## Step 7: Index the labels catalogue

This endpoint extracts text from the PDF and creates the local search index.

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/ingest" `
  -ContentType "application/json" `
  -Body '{"paths":["12594102_Labels_Decals.pdf"],"replace_index":true}'
```

Successful response example:

```json
{
  "message": "Catalogue indexed",
  "indexed_items": 30
}
```

`indexed_items` depends on the number of readable PDF pages. The resulting
index is saved to `models/catalog_index.json`, so it is available after a
server restart.

## Step 8: Search for a part or label

Send a natural-language description:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/search" `
  -ContentType "application/json" `
  -Body '{"query":"forklift battery warning sticker","limit":5}'
```

Request body fields:

| Field | Required | Description |
| --- | --- | --- |
| `query` | Yes | Product, scenario, or reference-number description. |
| `limit` | No | Number of results to return; 1 to 50. Default: 10. |

Each result includes the catalogue file, page number, relevance score, a text
excerpt, and any detected `REF xxxTAxxxx` article references.

## Step 9: Build recommendations from purchase history

The supplied `dummy_purchases.csv` is large. Start with 10,000 rows for a
quick demo, then remove `max_rows` or set it to `0` when you want to process
the full file.

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/recommendations/build" `
  -ContentType "application/json" `
  -Body '{"csv_path":"dummy_purchases.csv","max_rows":10000}'
```

The endpoint counts article pairs that appear in the same order. Its output is
saved to `models/recommendations.json` for reuse after restarting the API.

## Step 10: Get article recommendations

Use a reference number returned by the search endpoint:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/recommendations/REF%20111TA2234?limit=5"
```

Response example:

```json
{
  "reference_number": "REF 111TA2234",
  "recommendations": [
    {
      "reference_number": "REF 147TA5071",
      "co_purchase_count": 2
    }
  ]
}
```

## API reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Shows API status and data readiness. |
| `POST` | `/ingest` | Indexes PDF, TXT, or CSV catalogues. |
| `POST` | `/search` | Finds relevant catalogue content from a user query. |
| `POST` | `/recommendations/build` | Builds purchase-pair recommendations from CSV data. |
| `GET` | `/recommendations/{reference_number}` | Returns related articles for a selected reference. |

## Testing through Swagger UI

1. Open `http://127.0.0.1:8000/docs`.
2. Select an endpoint, for example `POST /search`.
3. Click **Try it out**.
4. Paste the JSON request body.
5. Click **Execute**.
6. View the response, status code, and generated cURL command.

## Evaluation for the interview

Use `app/evaluation/metrics.py` with 10-20 manually labelled customer queries.
It provides:

- Precision@K: how many returned results are relevant.
- Recall@K: how many expected results were found.
- Hit Rate@K: whether at least one relevant item was found.
- MRR: how early the first correct result appears.

## Suggested 15-minute presentation flow

1. Explain the business problem: customers cannot easily find the right part.
2. Show the architecture and why it works on a normal laptop.
3. Run `/ingest` once.
4. Run two or three realistic `/search` queries.
5. Show that each result links back to a source page and reference number.
6. Build recommendations from the dummy purchase data.
7. Show `/recommendations/{reference_number}`.
8. Explain the production upgrade path below.

## Production improvement plan

For a real TVH-scale deployment:

1. Store product data and structured attributes in a product-information
   database rather than PDF text only.
2. Combine exact reference matching, keyword search, and semantic vector search.
3. Run ingestion asynchronously and monitor failures.
4. Add user feedback, click-through data, and relevance evaluations.
5. Refresh recommendations in a scheduled data pipeline.
6. Add authentication, role-based access, observability, and CI/CD.

## Troubleshooting

### `uvicorn` is not recognized

Activate the virtual environment again, then run:

```powershell
python -m uvicorn app.main:app --reload
```

### Search returns no results

Call `POST /ingest` first. Also try a shorter query containing words that are
likely to occur in the catalogue.

### PDF indexing is too slow

Set `MAX_PAGES_PER_PDF=30` in `.env`, restart FastAPI, and try again.

### Recommendations are empty

Call `POST /recommendations/build` first. Ensure the reference number exists
in the purchase-history CSV and URL-encode spaces as `%20`.

## License

This project is a technical-case demonstration only. The supplied catalogue and
purchase data remain subject to their original owner and usage conditions.
