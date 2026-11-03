# Fabric workspace installation

`Install-IntoWorkspace.ps1` deploys the Bronze, Silver, Gold, and reporting layers. It creates or reuses all three Lakehouses, uploads the Bronze package, configures dependencies, imports seven notebooks plus the end-to-end pipeline, and deploys a refreshed semantic model with its bound report.

## Quick start

From the accelerator folder (`education/education-analytics`), run without arguments for the guided terminal installer:

```powershell
./deploy/Install-IntoWorkspace.ps1
```

The wizard asks for the workspace and offers four workflows:

| Workflow | Result |
| --- | --- |
| Preview only | Validate everything without changing Fabric |
| Deploy artifacts | Create or update Fabric items without running them |
| Build Bronze + Silver | Upload source data and populate Silver |
| Run full pipeline | Run Bronze, Silver, and Gold in dependency order |

It displays the complete plan and asks for confirmation before making changes. Existing `EDU_Config` content is preserved unless replacement is explicitly approved.

Full Pipeline defaults to replacing `EDU_Config`, because the deployed Gold notebooks and their helper contract must stay on the same version. Deploy-only workflows preserve an existing shared config by default.

For built-in help in any fresh session:

```powershell
Get-Help ./deploy/Install-IntoWorkspace.ps1 -Detailed
```

## Prerequisites

- PowerShell 7 or later.
- Python 3.11 or later for local sample validation.
- [Microsoft Fabric CLI](https://aka.ms/fabric-cli).
- An existing Fabric workspace on active capacity.
- Contributor or higher access to the target workspace.

Authenticate once before installation:

```powershell
fab auth login
fab auth status
```

Semantic-model binding and refresh use Power BI REST endpoints. The installer reaches them
through the Fabric CLI's own Power BI token (`fab api -A powerbi`), so this one sign-in
covers the whole deployment and no Azure CLI installation or second login is needed.

## Preview

Run from the accelerator folder (`education/education-analytics`). This validates the manifest, all 28 source CSVs, every notebook, and the pipeline definition without changing Fabric:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -PlanOnly
```

The scripted interface remains suitable for CI/CD and does not prompt when `-WorkspaceName` is supplied without `-Interactive`.
In CI or any redirected-input session, omitting `-WorkspaceName` fails immediately instead of opening the wizard.

## Install

Create the three Lakehouses, upload 29 Bronze landing files, and import all seven notebooks, the pipeline, semantic model, and report:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics"
```

To mirror workload ownership, provide a solution name. The installer creates or reuses that folder and derives the artifact prefix from the same value:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -SolutionName "North District"
```

This creates folder `North District` and artifacts such as `North_District_Bronze` and `North_District_BR_GD_Processing`. Rerunning with the same solution name updates that instance. Omitting `-SolutionName` retains the legacy workspace-root behavior and `-Prefix` option.

Add `-RunNotebook` to execute the Bronze load immediately after import:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -RunNotebook
```

Add `-RunSilverCreateSchemaNotebook` to create or validate the 24 Silver tables:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -RunSilverCreateSchemaNotebook
```

Add `-RunSilverTransformNotebook` to populate Silver from Bronze. The three source-layer switches can run in dependency order:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -RunNotebook `
    -RunSilverCreateSchemaNotebook `
    -RunSilverTransformNotebook
```

Use `-SkipBronzeDataUpload` for code-only deployments when the Bronze landing package is already present.

Add `-RunGoldCreateSchemaNotebook` to create or validate the 18 Gold tables:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -RunGoldCreateSchemaNotebook
```

Add `-RunEndToEndPipeline` with a reporting period to ingest Bronze, build Silver and publish Gold in one monitored run. The period bounds the attendance opportunity calendar and `-PeriodEnd` is exclusive:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -PeriodStart "2025-08-01" `
    -PeriodEnd "2026-06-01" `
    -RunEndToEndPipeline
```

The pipeline requires the Bronze landing manifest and source files. The installer uploads them unless `-SkipBronzeDataUpload` is supplied.

### The reporting period

`-PeriodStart` and `-PeriodEnd` are optional for installation but **required before the enrichment can run**. They decide which enrolled instructional days become attendance opportunities, so they cannot be defaulted: guessing them would silently change every attendance denominator.

- Supply both, as `YYYY-MM-DD`. `-PeriodEnd` is exclusive, so use the day after the last instructional day.
- Omit both and the enrichment notebook is still imported, but with its period unset. It refuses to run and names the missing parameters. Bronze and Silver installs are unaffected.
- `-RunEndToEndPipeline` requires the period; asking to run without it is an error rather than a silent empty load. The former `-RunSilverToGoldEnrichmentPipeline` name remains an alias for compatibility.
- To set the period after an install, either rerun the installer with it or edit the notebook's parameter cell in Fabric.

Choose the period from the Silver calendar. For the synthetic package that is two school years, `2024-09-02` to `2026-05-08` inclusive, so `-PeriodStart 2024-09-01 -PeriodEnd 2026-05-09`. Include the previous school year so the year-on-year measures have something to compare with.

The default resource names are `EDU_Bronze`, `EDU_BR_CreateSchema`, `EDU_BR_Ingestion`, `EDU_SL`, `EDU_SL_CreateSchema`, `EDU_BR_SL_Transform`, `EDU_GD`, `EDU_Config`, `EDU_GD_CreateSchema`, `EDU_SL_GD_Enrichment` (notebook), and `EDU_BR_GD_Processing` (pipeline). Override base names when required:

```powershell
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EducationAnalytics" `
    -Prefix "DEV_" `
    -LakehouseBaseName "Education_Bronze" `
    -BronzeSchemaNotebookBaseName "BR_CreateSchema" `
    -NotebookBaseName "BR_Ingestion" `
    -SilverLakehouseBaseName "SL" `
    -SilverNotebookBaseName "SL_CreateSchema" `
    -GoldLakehouseBaseName "GD" `
    -GoldNotebookBaseName "GD_CreateSchema" `
    -EnrichmentNotebookBaseName "SL_GD_Enrichment" `
    -ProcessingPipelineBaseName "BR_GD_Processing" `
    -RunSilverCreateSchemaNotebook `
    -RunGoldCreateSchemaNotebook
```

## Installed layout

The script uploads the existing source package without regenerating it:

```text
EDU_Bronze.Lakehouse/
└── Files/
    └── landing/
        └── education-analytics/
            ├── manifest.json
            ├── PowerSchool/
            ├── Canvas/
            ├── Moodle/
            └── NWEA/
```

The imported notebook uses `EDU_Bronze` as its default Lakehouse. When run, it creates 28 source-qualified Delta tables and `ingestion_audit`; `ingestion_quarantine` is created only if malformed rows are found.

`EDU_BR_CreateSchema` reads the landing manifest, creates or verifies 28 source-qualified Bronze tables plus `ingestion_audit` and `ingestion_quarantine`, and rejects unsafe schema drift. It never loads source rows. `EDU_BR_Ingestion` validates and loads source files only into those pre-created tables.

`EDU_SL_CreateSchema` embeds the physical Silver contract so workload users receive one self-contained artifact. It creates missing Silver tables, skips exact schema matches, and rejects unsafe schema drift. It never populates or truncates Silver business data. Repository tests compare the embedded contract with the design CSVs, which are not uploaded to Fabric.

`EDU_BR_SL_Transform` reads Bronze Delta tables, validates changed targets, and populates the 24 Silver business tables. Unchanged targets are skipped using Delta-version fingerprints.

`EDU_Config` carries the shared table helpers, data-quality assertions, `BaseDataModel` and the Gold writer. Both Gold notebooks load it with `%run`, and the installer rewrites that reference to the deployed item name. Lakehouse names, schema names and the reporting period are substituted into temporary copies only, so the checked-in definitions keep their placeholders.

`EDU_GD_CreateSchema` declares `EducationGoldModel` and creates the 17 Gold tables plus the `GoldPublication` control table. `EDU_SL_GD_Enrichment` validates its Silver inputs, rebuilds each target for one snapshot, validates the outputs and publishes only after every target succeeds. `EDU_BR_GD_Processing` runs Bronze schema creation, source ingestion, Silver schema creation, Bronze-to-Silver transformation, Gold schema creation and Silver-to-Gold enrichment in strict success order with concurrency 1.

Gold uses a full refresh per snapshot. Each target is appended as a candidate stamped with one `snapshot_id` and one `as_of`, validated through views scoped to that candidate, and published only when every target passes. Publication appends the `GoldPublication` row, which moves the published pointer; the superseded snapshot is retired only afterwards. A refresh that fails partway therefore leaves the previously published snapshot complete and still named by the newest publication row.

`snapshot_id` is a fingerprint of the transformation version, the reporting period and the exact Delta version of every Silver input, so a retry over unchanged inputs reuses the same identity and replaces its own rows instead of duplicating facts.

`EDU_GD_CreateSchema` materialises the columns the current use cases depend on, which is deliberately narrower than the full design in `docs/data-models/Gold_Data_Model.csv`. Treat the deployed schema, not the CSV, as the column contract when building anything on top of Gold.

`EDU_Analytics` queries only the latest row published by `GoldPublication`, so retained candidate or superseded snapshots cannot create duplicate model keys. The installer imports the model and `EDU_Insights` bound to it, then provisions or reuses the workspace identity, grants it Viewer access, and binds the model to a shareable SQL connection with workspace-identity credentials. An existing connection is reused only when it is shareable and already carries workspace-identity credentials, because a personal or OAuth connection over the same endpoint matches on type and path just as well and cannot serve an unattended refresh. No client secret is stored.

Each Gold table resolves its own snapshot, and fourteen independent lookups agree only while nothing publishes. So the installer resolves the published snapshot once, pins `GoldSnapshotId` to it for the duration of its refresh and clears it afterwards: one refresh loads one consistent bundle, and later scheduled refreshes go back to following the published pointer.

Reporting is deployed last, after any requested notebook or pipeline run, because the model imports from Gold. When `EDU_GD` holds no published snapshot yet — a Bronze-only or deploy-only install — both items are still created but the refresh is skipped with a warning rather than failing the run. The gate is a publication row, not the `GoldPublication` table: the Gold schema notebook creates that table empty, so a schema-only run would otherwise refresh and report a successful but empty model. Rerun with `-RunEndToEndPipeline` to populate Gold and refresh the model.

Reinstalling is safe for configuration: a run without `-PeriodStart` preserves the reporting period already configured in the deployed notebook rather than blanking it, and the shared `EDU_Config` notebook is left alone unless `-OverwriteSharedConfigNotebook` is supplied.

## Incremental reruns

The notebook sets `skip_unchanged_files = True` by default. For each source file it compares the current SHA-256 with the latest successful audit record for the same source instance. When the hash and expected row count match, the prior run had no rejected rows, and the target table still exists, the notebook records `SKIPPED_UNCHANGED` without parsing the CSV or rewriting the Delta table.

The small `ingestion_audit` table still receives one status row per source file on every run. Set `skip_unchanged_files = False` through the notebook parameter cell or pipeline parameters when a full Bronze rebuild is required.

## Reruns

The installer is safe to rerun for the same workspace and names:

- An existing Lakehouse is reused.
- The known landing files are overwritten in place.
- The notebook definition is updated in place, except the shared `EDU_Config` notebook, which is kept unless `-OverwriteSharedConfigNotebook` is supplied.
- A configured reporting period is preserved when the rerun does not supply one.
- A period-less enrichment notebook remains period-less and does not block a rerun.
- The retired enrichment pipeline is kept unless `-RemoveRetiredPipeline` is explicitly supplied or approved in the wizard.
- Existing source-instance rows are replaced by the ingestion notebook.
- Unchanged Silver targets are not rewritten.
- Gold is rebuilt as a new candidate snapshot and published atomically, so a retry does not duplicate fact rows and an interrupted run does not leave a mixed model.

The installer does not delete a Lakehouse, unrelated OneLake files, or unrelated workspace items.

Job submission is not proof of success. Each requested run is polled to a terminal state, and a failed, cancelled or timed-out job fails the installation command.

## Troubleshooting

- `Fabric CLI is not authenticated`: run `fab auth login`.
- `Fabric workspace not found`: verify the workspace name and your workspace role.
- Local validation failure: run `python "sample-data/generate.py" --check` and do not mix CSV and manifest versions.
- Notebook job failure: open the imported notebook in Fabric and review Spark output and the default Lakehouse connection.
- Semantic model setup failure: verify `fab auth status` shows the Fabric tenant and that the operator can manage workspace identity, connections, and Power BI datasets.

## Operator notes

- Run `-PlanOnly` first for a new environment or changed package.
- Use `-SkipBronzeDataUpload` for code-only updates after source files exist.
- Use `-RemoveRetiredPipeline` only after confirming that the exact legacy pipeline can be deleted.
- Use `-OverwriteSharedConfigNotebook` when running Gold against an existing installation. Gold execution stops rather than mixing new notebooks with stale shared helpers.
- `-SkipLocalValidation` skips the sample-data checks only. Python remains required by `-PlanOnly` to compile generated notebook code.
- Gold enrichment requires both reporting dates; `PeriodEnd` is exclusive.
- Jobs are polled to a terminal state. Submission alone is never reported as success.
- The installer stores no credentials. Authenticate with `fab auth login` before deployment.

Execution order:

```text
Bronze Lakehouse + ingestion
    -> Silver Lakehouse + schema
    -> Bronze-to-Silver transform
    -> Gold Lakehouse + shared config + schema
    -> Silver-to-Gold enrichment pipeline
    -> Semantic model + report, refreshed from published Gold
```

If deployment stops, inspect the reported item or job, correct the issue, and rerun the same command. Resource creation and imports are designed to be idempotent.

## Maintainer verification

After changing the installer, run these checks from the accelerator folder (`education/education-analytics`):

```powershell
# PowerShell syntax
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path "deploy/Install-IntoWorkspace.ps1"),
    [ref]$tokens,
    [ref]$errors
) | Out-Null
$errors

# Full generated-artifact validation without Fabric changes
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EDUCATION-ANALYTICS" `
    -PlanOnly `
    -SkipBronzeDataUpload `
    -PeriodStart "2024-09-01" `
    -PeriodEnd "2026-05-09"

# Diff hygiene
git diff --check
```

The expected result is zero parser errors, `[OK] Preview passed`, and no diff-check output.