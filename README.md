# Mflix Reflex Browser (PyMongo + MongoDB Sample Dataset)

A basic single-page application (SPA) built with **Reflex** + **PyMongo** that lets you **search and filter** the MongoDB **sample_mflix** movie catalog. It includes **two toggleable result views** (Cards + Coverflow), **configurable page size**, and **coverflow preloading** for seamless pagination.

## Features

- **Search** movies by title/plot (simple regex match)
- **Filter** by:
  - Genre (auto-populated from the dataset)
  - Min/Max year
- **Two views**
  - **Cards view**: grid of movie cards
  - **Coverflow view**: horizontal “coverflow-ish” poster strip with a selected state
- **Page size dropdown**: `10`, `25` (default), `50`, `100`
- **Pagination**
  - Cards: classic page-by-page
  - Coverflow: **preloads the next `<page_size>` results** so “Next” swaps instantly

## Tech Stack

- **Reflex** (Python-first web framework for SPAs)
- **PyMongo** (MongoDB driver for Python)
- **MongoDB Atlas** + **Sample Dataset: `sample_mflix`**
- `python-dotenv` for env var loading
- `certifi` to simplify TLS CA handling (useful for Atlas connections)

## Prerequisites

- Python 3.10+ (recommended)
- A MongoDB deployment with the **Sample Mflix dataset** loaded:
  - Database: `sample_mflix`
  - Collection: `movies`
- A MongoDB connection string (Atlas recommended)

## Project Structure (typical)

Depending on the name you chose during `reflex init`, you should have something like:

```

mflix_reflex/
.env
requirements.txt (optional)
mflix_reflex/
mflix_reflex.py   <-- main app (State + UI)
rxconfig.py

````

## Setup

### 1) Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
````

### 2) Install dependencies

```bash
pip install reflex pymongo certifi python-dotenv
```

### 3) Initialize Reflex (if you haven’t already)

```bash
reflex init
```

Choose a blank template when prompted.

## Configuration

Create a `.env` file at the project root:

```dotenv
MONGODB_URI="mongodb+srv://<user>:<pass>@<cluster>/<optional_db>?retryWrites=true&w=majority"
MFLIX_DB="sample_mflix"
MFLIX_COLLECTION="movies"
```

### Notes

* `MFLIX_DB` and `MFLIX_COLLECTION` are optional (defaults match the sample dataset).
* If your Atlas IP access list is restricted, make sure your current IP is allowed.

## Run the App

```bash
reflex run
```

Then open:

* [http://localhost:3000](http://localhost:3000)

## How It Works

### Querying & Pagination

* The app builds a MongoDB query from the UI filters (search text, genre, year range).
* Results are sorted by `title` and fetched using `skip`/`limit` based pagination.

### Coverflow “Preload Next Page”

In **Coverflow mode**, the app fetches **2× page_size** results per request:

* First `page_size` = current page to render immediately
* Next `page_size` = stored as a **preload buffer**

When you click **Next**:

1. The UI swaps in the preload buffer immediately.
2. A background event refills the next preload buffer.

This gives the “instant next page” feel without waiting on the network on each click.

## Usage Tips

* Try searching for common titles like: `star`, `love`, `war`
* Use genre filtering to narrow a large result set quickly.
* Coverflow is best experienced with a larger page size (e.g., 50) if you want more posters to scroll through.

## Troubleshooting

### “ServerSelectionTimeoutError” / cannot connect

* Double-check `MONGODB_URI`
* Confirm your Atlas **IP Access List** allows your current IP
* Ensure your cluster is running and credentials are correct

### No movies show up / zero results

* Verify the **Sample Mflix dataset** is loaded into your cluster
* Confirm `MFLIX_DB=sample_mflix` and `MFLIX_COLLECTION=movies`

### Posters missing

Some entries may not have posters; the UI uses a simple placeholder to keep layout stable.

## License

MIT (or your preferred license).

