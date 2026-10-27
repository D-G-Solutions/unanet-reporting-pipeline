# Azure deployment handoff

Application code is supplied here. IT provisions resources, access and network connectivity, reviews the image/driver, and applies company deployment standards. Reporting owners validate/maintain the transformations and change the Power BI connections.

| Resource | Required use |
|---|---|
| Resource group, East US 2 | Existing subscription; one production environment initially |
| Container Apps environment and scheduled Job | Consumption workload; baseline 2 vCPU / 4 GiB; tune after pilot |
| Container Registry | Basic baseline; build/push approved image |
| Key Vault | Store read-only Unanet connection secret; allow job identity access |
| Blob Storage | StorageV2, Hot, LRS baseline, private container; raw and processed prefixes |
| Managed identity | Blob Data Contributor for publication and AcrPull for image; Key Vault access as approved |
| Monitoring | Capture exit status/logs; alert on failure; retention/lifecycle policy |

Configure one replica per execution (parallelism 1; completion count 1), no overlapping manual/scheduled runs, and no automatic retries initially. Parallelism 1 does not itself prevent separate executions overlapping. Set a generous pilot timeout (e.g. 10,800 seconds), then tune to observed extraction/transformation/upload duration. UTC cron is used; monthly close dates and holidays are business-controlled, so start manually after close and enable the agreed schedule later. A cron date does not verify that finance has closed.

Environment: UNANET_ODBC_CONNECTION_STRING (Key Vault-backed secret reference), AZURE_STORAGE_ACCOUNT_URL, AZURE_STORAGE_CONTAINER, optionally AZURE_CLIENT_ID for user-assigned managed identity. Never bake secrets into an image or Git. Script reads environment variables, not the vault API directly.

Baseline container command is `python -m unanet_pipeline.refresh --odbc --output-dir /data --publish`. The included configuration's publication approval flag must be reviewed/enabled after real-data reconciliation. `/data` needs enough ephemeral disk for all selected raw rows, SQLite working data/indexes, and JSON outputs; size this from the pilot. 4 GiB is a starting memory allocation, not a verified capacity requirement. No local files are durable across executions; successful uploads are durable in Blob.

Before deployment, verify approved Linux ODBC driver/runtime support, source authentication, DNS/network/TLS access, correct catalog/schema, least-privilege access to all 34 tables, image build, managed identity permissions and storage connectivity. If the approved driver cannot run on Linux, resolve a supported extraction API/runtime with Unanet before committing to this image. The current code implements ODBC, not a speculative Unanet API.

Before production, reconcile against a consistent real baseline, test a manual cloud execution and failure handling, confirm Power BI can refresh from Blob with approved authentication/network settings, and coordinate publication versus Power BI refresh. Set raw/processed retention according to company policy; do not delete a run still referenced by a pinned Power BI refresh or latest pointer.

This package provisions no Azure resources and starts no paid services. It requires no Azure SQL database, separate Logic App scheduler, Azure Batch or permanent gateway VM for the proposed cloud Blob path. It does not provide a contractual cost ceiling. Runtime, storage/retention, logging and networking should be measured in the pilot before revising the existing estimate.
