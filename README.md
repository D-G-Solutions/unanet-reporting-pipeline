# Unanet scheduled reporting refresh — version 0.2.1

This package was built from the semantic model inside the October 8, 2026 Enterprise Dashboard project ZIP. It extracts 34 Unanet/Data Virtuality source tables once per run and prepares 26 reporting tables. It is a locally tested implementation awaiting real-data reconciliation and live connection validation. Your Power BI project has not been changed.

The job reads Unanet, saves projected raw data, performs the Power Query joins/appends in Python using a temporary local SQLite file, and writes processed JSON files to Azure Blob Storage. SQLite is scratch storage inside the container, not an Azure SQL database. No SQL service is required.

## Start here on Windows

Install Python 3.12 or later. Extract this ZIP, open the `unanet-refresh` folder in VS Code, and open its terminal. You should see `run_refresh.py` in that folder. CSV mode and tests need only Python's standard library.

```powershell
py -m unittest discover -s tests -v
py run_refresh.py --csv-dir examples/full_source --output-dir data/demo
```

The included CSVs are **synthetic examples**, not your company's exported data. The tests verify cost formulas, joins with missing/duplicate/null matches, numeric validation, planned weekdays, output scope, renames, chunking, reconciliation controls and publication ordering with a fake Azure SDK. Passing them does not establish agreement with your real report or prove Azure connectivity.

Open `data/demo/latest.json`. Its `manifest` value identifies the run's manifest file. Open that file to find each table's JSON files, row counts and cost totals. The demo Project Cost Details has four rows: Labor 200, Expense 50, Financial Document Expense 125, Financial Document Labor 80. Planned hours span Friday September 4 and Monday September 7, with eight hours each.

## Test with actual exports

Use `docs/source_inventory.md` and `config/refresh.json` for exact source tables and required columns. Put one CSV per source in a local `real_source` folder, named exactly like `person_time_data.csv`. CSV headers must be source column names, not renamed model labels. Additional columns are ignored; missing required columns fail. UTF-8 with or without BOM is supported. Dates must be ISO (`2026-09-30` or `2026-09-30T00:00:00`), numbers unformatted (`1234.50`, no currency symbols/thousands separators), booleans true/false or 1/0. Blank CSV fields are null. The live ODBC adapter preserves empty text separately from null.

Use exports from the same source period as the Power BI baseline. An export of already-joined Project Cost Details is a comparison baseline, **not a substitute for the raw source CSVs**. Some required sources are intermediate Power Query queries, rather than loaded model tables. The earlier cost-only CSV runner remains available (`run_pipeline.py`, eleven sources under `examples/source`) for a smaller pilot; use `run_refresh.py` for the full Azure pipeline.

```powershell
py run_refresh.py --csv-dir real_source --output-dir data/pilot
py tools/compare_cost_export.py --power-bi-csv exports/ProjectCostDetails.csv --manifest data/pilot/runs/YOUR_RUN_ID/processed/manifest.json
```

Use a full, underlying Power BI export with `Cost Source` and `Cost Amount`, without visual aggregation or truncation. The comparison checks row counts, totals and null amounts by source. Also reconcile table counts, keys/dates, planned hours, financial-close behavior and important report measures. This tool does not prove row-by-row equality. Export limits or a filtered baseline can produce a misleading mismatch.

Each run generates `controls.json`. For a repeat run against the **same frozen input**, pass `--controls path/to/controls.json` to require matching row counts and cost totals for all outputs. Do not use fixed historical controls for a changing monthly source. Thresholds and production reconciliation should be reviewed before approval.

## Live extraction after IT provides access

Install optional dependencies in a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[odbc,azure]"
.\.venv\Scripts\python.exe run_refresh.py --odbc --output-dir data/pilot
```

IT must install/configure the approved Unanet/Data Virtuality ODBC driver and connection. The source model uses the `DataVirtualityUnicode` DSN, database `datavirtuality`, schema `dngspt`. The connection must select the correct database/catalog; Python selects tables under the configured schema. The script reads `UNANET_ODBC_CONNECTION_STRING` from the environment; it does not read `.env` files automatically. Do not commit credentials, real exports or output data. Use a read-only Unanet identity.

For Azure, set `AZURE_STORAGE_ACCOUNT_URL` to the account HTTPS URL without SAS and `AZURE_STORAGE_CONTAINER` to the private container. Azure SDK DefaultAzureCredential uses the job's managed identity. Supply the Unanet connection string through a Key Vault-backed Container Apps secret/environment reference. No Azure account key is needed by this job.

After real-data checks and IT review, set `approved_for_production` to `true` in the reviewed config and add `--publish`. The flag starts false to prevent accidental publication of the example data. Store production data in a separate private container/account from any pilot data.

## Processing and publication

- Full extraction on each execution; incremental watermarks and per-table monthly/daily caching are not implemented. Start with a manually triggered monthly job after financial close. A future daily schedule would reread all 34 sources.
- Each source is streamed in batches into disk-backed SQLite; joins run locally against indexed keys. Duplicate matches are retained; no silent deduplication. Outputs are JSON arrays partitioned at 50,000 rows (configurable), including an empty array/schema for empty tables.
- Raw files are projected to the allowed columns, not unrestricted source dumps. Output manifests carry file hashes, schema, row counts, durations and cost totals. Source minimum-row checks are configured for core outputs; empty optional tables are allowed.
- Uploads use immutable `raw/<run_id>/` and `processed/<run_id>/` folders. `processed/latest.json` changes only after upload completes, with an ETag concurrency guard. A failed run leaves the previous pointer intact; partial immutable folders can remain and need lifecycle cleanup. An older run cannot replace a newer published run.
- This is not a transactional snapshot of Unanet: queries execute sequentially. Use a quiet source window or ask Unanet for a supported snapshot method. Do not launch overlapping jobs.
- No global cutoff is imposed. The model has planned/future operational data as well as finance data. Fiscal Period Close remains available for existing Power BI measures to apply the correct closed period.
- Logs show table names/counts only. Driver/Azure failures return a nonzero exit code without printing connection strings. Configuration/conversion errors identify validation failure; investigate using a secure local environment.

## Power BI cutover is a separate step

Replace all 26 loaded Unanet query outputs with the corresponding processed Blob tables, keeping names, column types, relationships, calculated columns and DAX measures. Leave SharePoint and local/DAX tables as they are. Read `processed/latest.json`, its manifest, and only the files listed for the requested table/run; do not combine every historical JSON in a folder or include raw files/manifest/pointer JSON as data. Empty outputs need the manifest's schema applied explicitly.

A refresh must consume a **single completed run**. For the initial monthly setup, finish publication, keep the pointer stable throughout the Power BI refresh, then allow the next publication. For stricter orchestration, pin a run ID for the refresh and update it between refreshes. Resolving `latest.json` independently in each query can mix runs if publication overlaps refresh. Source success does not automatically trigger a Power BI service refresh in this implementation; configure its schedule separately or add orchestration later.

The gateway-free goal depends on IT approving a cloud-accessible Blob endpoint and supported Power BI authentication. Private-only network paths may change that design. Removing the loaded ODBC queries is essential; retained loaded ODBC dependencies can still require a gateway. The pipeline cannot promise a specific Power BI refresh time.

## Azure handoff

See `docs/azure_handoff.md`. The Dockerfile is a baseline and **does not contain the vendor ODBC driver**. IT must confirm approved Linux driver availability/licensing and install it before a production image can extract data. This is a real deployment dependency; the Windows DSN cannot simply be copied to Linux.

Reference documentation:
- Container Apps jobs: https://learn.microsoft.com/en-us/azure/container-apps/jobs
- Managed identity image pull: https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull
- Blob connector: https://learn.microsoft.com/en-us/power-query/connectors/azure-blob-storage
- Azure Python Blob SDK: https://learn.microsoft.com/en-us/python/api/azure-storage-blob/

## Driver timeout compatibility fix (0.2.1)

The observed Data Virtuality driver rejects timeout connect attribute 113 (`SQLSetConnectAttr`). The ODBC adapter now continues using driver defaults for that specific unsupported-attribute error, prints a warning, and still fails on other driver errors. The requested `--query-timeout` is not enforced in this fallback. Retain the Azure job execution timeout as the outer limit. A local pilot can be stopped with Ctrl+C. This compatibility path is covered by three mocked-driver tests; live extraction still needs validation.
