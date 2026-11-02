# Education analytics

Education analytics brings student information, learning management and assessment data into a
Microsoft Fabric medallion lakehouse and adds a Power BI report on attendance, enrollment, coursework
and student performance. A Fabric workload provides guided deployment from inside Microsoft Fabric.

The accelerator ships with a synthetic school district and source-shaped files for PowerSchool,
Canvas, Moodle and NWEA MAP Growth, so it can be deployed and explored without access to real data.

## Architecture

```text
Source CSV files  ->  Bronze Lakehouse  ->  Silver Lakehouse  ->  Gold Lakehouse  ->  Semantic model  ->  Power BI report
(sample-data)         EDU_BR_*              EDU_SL_*              EDU_GD_*            (SQL endpoint)
                      \___________________ EDU_BR_GD_Processing pipeline ___________________/
```

- **Bronze** lands the source files unchanged in source-qualified tables.
- **Silver** conforms the four sources into one education data model.
- **Gold** builds the reporting star schema and publishes versioned snapshots.
- **Power BI** reads the Gold Lakehouse through a semantic model and report.

## What's included

| Folder | Contents |
| --- | --- |
| [`deploy/`](deploy/) | `Install-IntoWorkspace.ps1` installer for a Fabric workspace |
| [`src/fabric/notebooks/`](src/fabric/notebooks/) | Seven Fabric notebooks for Bronze, Silver and Gold |
| [`src/fabric/pipelines/`](src/fabric/pipelines/) | `EDU_BR_GD_Processing` end-to-end pipeline |
| [`src/fabric/workload/`](src/fabric/workload/) | React/TypeScript Fabric workload for guided deployment |
| [`src/power-bi/`](src/power-bi/) | Semantic model and report (PBIP/TMDL) |
| [`sample-data/`](sample-data/) | Synthetic district: manifest and 28 source CSV files |
| [`docs/data-models/`](docs/data-models/) | Silver and Gold model, relationship and calculation definitions |
| [`docs/use-cases/`](docs/use-cases/) | Use cases and report walkthrough |

Fabric artifacts follow `<solution>_<layer>_<action-or-flow>` naming, using `EDU`, `BR`, `SL` and
`GD`; for example `EDU_Config`, `EDU_SL_CreateSchema` and `EDU_BR_GD_Processing`.

## Prerequisites

- A Microsoft Fabric workspace on active capacity, with Contributor or higher access.
- PowerShell 7 and the [Fabric CLI](https://aka.ms/fabric-cli) (`fab`) for the installer.
- Python 3.11 or later to validate or regenerate sample data.
- Node.js 22.15 or later only if you build or run the Fabric workload.

See [deploy/README.md](deploy/README.md) and [src/fabric/workload/README.md](src/fabric/workload/README.md)
for the full requirements.

## Deploy

Run commands from this folder (`education/education-analytics`). Paths in this accelerator's
documentation are relative to this folder unless stated otherwise.

Run without arguments for the guided installer:

```powershell
./deploy/Install-IntoWorkspace.ps1
```

For scripted deployment:

```powershell
fab auth login
./deploy/Install-IntoWorkspace.ps1 `
    -WorkspaceName "EDUCATION-ANALYTICS" `
    -RunNotebook `
    -RunSilverCreateSchemaNotebook `
    -RunSilverTransformNotebook
```

The Silver-to-Gold enrichment also needs a reporting period (`-PeriodStart` / `-PeriodEnd`, end
exclusive). See [deploy/README.md](deploy/README.md) for preview, naming and troubleshooting options.

To deploy from inside Fabric instead, build and register the workload described in
[src/fabric/workload/README.md](src/fabric/workload/README.md).

## Cost

Cost comes from the Fabric capacity that runs the notebooks, pipeline, Lakehouses and semantic model
refresh, and from Power BI licenses for report users. Pause or scale down the capacity when it is not
in use.

## Limits

- Source connectors are not included. Source data is landed as CSV files that match the sample package.
- The sample data is synthetic and does not prove compatibility with a specific tenant or source version.
- Workspace folder APIs used by the workload are currently in preview.

## Data and privacy

The repository contains synthetic data only. Once deployed with real data, the accelerator processes
student, staff, enrollment, attendance, coursework and assessment records inside your own Microsoft
Fabric tenant. Microsoft does not receive this data, and the accelerator sends no telemetry. You are
responsible for access control, retention and compliance with applicable education privacy laws.
