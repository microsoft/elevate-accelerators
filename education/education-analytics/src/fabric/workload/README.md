# Education Analytics Fabric workload

This project is the React/TypeScript solution home for the Education Analytics Fabric assets. It is based on the official Microsoft Fabric Extensibility Toolkit at commit `dacab1b391d03010ba61a0446126d05515c487f0` and retains the upstream MIT license.

The workload intentionally has no custom backend. Each `EducationSolution` item owns one workspace folder and deploys its artifact package through delegated Fabric APIs. The item name determines the folder name and artifact prefix; persisted folder and item IDs determine ownership on later updates.

Power BI is part of the managed package. Deployment creates a semantic model over the owned Gold Lakehouse, binds it to a secretless workspace-identity SQL connection, and deploys the bound report. Fresh installs refresh after the first successful end-to-end pipeline run; package updates refresh immediately against the existing Gold publication.

## Experience

- **Setup**: three steps to review the derived folder, artifact prefix, and managed package before deployment.
- **Overview**: deployed artifact inventory, latest processing job, reporting readiness, and medallion flow.
- **Data**: native links to Bronze, Silver, Gold, and the end-to-end pipeline, plus safe on-demand execution.
- **Reports**: opens the managed native Power BI report after deployment.

The workload deploys three Lakehouses, seven notebooks, one Data Pipeline, one semantic model, one report, and the versioned synthetic source package. Bronze schema creation is separate from source ingestion. The browser deployment uploads the manifest and 28 CSVs to `Files/landing/education-analytics` in the owned Bronze Lakehouse.

## Prerequisites

- Node.js 22.15 or later.
- PowerShell 7 or later.
- NuGet CLI available on `PATH`.
- .NET 8 runtime for DevGateway.
- Azure CLI for Entra app creation.
- A Fabric tenant, capacity-backed development workspace, and permission to develop workloads.
- A multitenant Entra SPA application with the Fabric workload sign-in redirect URIs.
- Tenant admin consent for `Workspace.ReadWrite.All`, `Connection.Read.All`, `Connection.ReadWrite.All`, and `Dataset.ReadWrite.All` in addition to the core Fabric item scopes.

The setup script creates a frontend-only SPA registration and does not create a client secret. Run Azure CLI in the same tenant used by Fabric.

## Configure

From `src/fabric/workload`:

```powershell
./scripts/Setup/SetupWorkload.ps1 `
    -HostingType FERemote `
    -WorkloadName "Org.EducationAnalytics" `
    -WorkloadDisplayName "Education Analytics" `
    -FrontendAppId "<frontend-app-id>"
```

Confirm these generated values in `Workload/.env.dev`:

```dotenv
WORKLOAD_NAME=Org.EducationAnalytics
ITEM_NAMES=EducationSolution
ENABLE_PLAYGROUND=false
```

Environment files contain deployment identifiers and are ignored by Git. Do not place secrets in them.

Fabric workload manifest images must be PNG. SVG remains suitable for ordinary frontend assets but Fabric rejects SVG files inside the manifest package.

To regenerate the three Workload Hub PNGs without changing the item icon:

```powershell
python -m pip install -r ./scripts/Build/requirements.txt
python ./scripts/Build/GenerateWorkloadHubImages.py
```

The generator is deterministic and writes the exact dimensions referenced by `Manifest/Product.json`. Review all three outputs visually before committing them.

## Develop

Run the DevGateway and frontend in separate PowerShell terminals:

```powershell
./scripts/Run/StartDevGateway.ps1
./scripts/Run/StartDevServer.ps1
```

The Fabric-hosted iframe does not use webpack hot reload because replacing the workload entry loses Fabric bootstrap metadata. Source changes rebuild automatically; reopen or reload the Fabric item after compilation completes.

For your development tenant, open:

```text
https://app.fabric.microsoft.com/workloadhub/detail/Org.EducationAnalytics.Product?experience=fabric-developer
```

If the workload is not visible, enable **Fabric Developer mode** under Fabric settings and confirm both local processes are still running. DevGateway authentication should use its interactive mode; the noninteractive option places a short-lived token in process arguments and is intended only for controlled automation.

Create an **Education Solution** item in the configured Fabric development workspace. For an item named `North District`, deployment creates the `North District` folder with these core artifacts:

| Artifact | Expected name | Required |
| --- | --- | --- |
| Bronze Lakehouse | `North_District_Bronze` | Yes |
| Silver Lakehouse | `North_District_SL` | Yes |
| Gold Lakehouse | `North_District_GD` | Yes |
| Processing pipeline | `North_District_BR_GD_Processing` | Yes |

All seven notebooks use the same `North_District_` prefix. Deployment never maps an Education item to arbitrary workspace artifacts. It creates or resumes artifacts only inside the owned folder and uses persisted IDs for later updates; a deleted managed artifact is recreated on the next deployment. A schema-v1 item is migrated once by validating its bound core IDs and the six notebook IDs referenced by its pipeline before those artifacts are moved; unrelated root items are not moved.

Sample data upload is selected by default for the first deployment and disabled by default for updates. Select **Upload or refresh Bronze sample data** only when the 28 packaged CSVs and manifest should overwrite the corresponding Bronze landing files. Files are transferred as bytes so their original encoding is preserved.

Workspace folder APIs are currently preview, and Fabric Git integration does not include workspace folder structure. Semantic model and report names must still be unique across the workspace.

## Validate

From `src/fabric/workload/Workload`:

```powershell
npm ci
npm test
npm run typecheck
npm run build:test
npm audit
```

From `src/fabric/workload`:

```powershell
./scripts/Build/BuildManifestPackage.ps1 -Environment test -ValidateFiles $true
```

Webpack reports a large vendor chunk from Fluent UI. This is a performance warning, not a build failure.

## Build and publish

```powershell
./scripts/Build/BuildRelease.ps1 `
    -WorkloadName "Org.EducationAnalytics" `
    -FrontendAppId "<frontend-app-id>" `
    -WorkloadVersion "0.5.0" `
    -Environment prod
```

The release contains the static SPA and manifest package. Deploy the SPA to an approved HTTPS endpoint and upload the manifest package through Fabric workload management.

## Smoke test

1. Keep `StartDevServer.ps1` running and confirm `http://127.0.0.1:60006/manifests_new/metadata` returns HTTP 200.
2. Run `StartDevGateway.ps1` with its default interactive authentication and complete the Microsoft sign-in window.
3. In Fabric, enable **Developer settings > Fabric Developer mode**.
4. Open `https://app.fabric.microsoft.com/workloadhub/detail/Org.EducationAnalytics.Product?experience=fabric-developer`.
5. Create an **Education Solution** item in your development workspace.
6. Select **Deploy package** and confirm a folder named after the Education item contains all thirteen prefixed artifacts and the Bronze Lakehouse contains the manifest plus 28 source CSVs.
7. Save, reopen the item, and verify Overview, Data, and Reports. Do not run end-to-end processing unless Bronze source files are present and the configured reporting period is intended for a new Gold publication.

Fabric manifest item files use frontend schema `1.100`, and manifest images are PNG because Fabric rejects SVG files in workload packages.

## Deployment behavior

- Existing artifacts are reused and updated without creating duplicates.
- The Fabric-generated `EDU_Bronze_EventhouseEndpoint` Eventhouse and KQL Database are removed while the Lakehouse SQL endpoint is preserved.

The browser package ships the seven artifact definitions and the active synthetic source package. The first deployment uploads all manifest-listed CSVs to the owned Bronze Lakehouse; updates leave them unchanged unless sample refresh is selected. Deployment does not execute notebooks automatically.

## Partner extension points

Partners should customize only:

- workload/item identity and Entra registration;
- manifest copy, imagery, support URLs, and publisher information;
- expected Fabric artifact names and types;
- status content and native artifact destinations;
- semantic model/report branding and measures; and
- semantic-model roles.

Do not introduce a package registry, custom backend, direct OneLake browser access, or custom reporting framework without a concrete requirement and security review.

## Operational boundary

The deployment package includes three Lakehouses, all seven notebooks, the `EDU_BR_GD_Processing` pipeline, semantic model, report, and an optional refresh of the 28 synthetic source CSVs. It does not execute notebooks automatically. After source data is available, the workload runs all six stages from Bronze schema creation through Gold enrichment in one native Fabric pipeline.