# Accelerator standards

Every accelerator in this repository follows these standards so customers and partners get a
consistent experience.

## Location and naming

- Place the accelerator under its sector: `education/`, `nonprofit/`, or a new sector folder
  agreed with the maintainers.
- Use lowercase kebab-case folder names.
- Name the accelerator after its scenario, not its technology, for example `education-analytics`
  rather than `fabric-notebooks`.
- Put assets in `shared/` only when two or more accelerators use them.

## Required layout

```text
<sector>/<accelerator-name>/
├── README.md               Scenario, architecture, prerequisites, deploy, cost, limits
├── accelerator.json        Catalog metadata
├── CHANGELOG.md
├── THIRD-PARTY-NOTICES.md  Only when third-party components are included
├── docs/                   Architecture, use cases, specifications, data model
├── deploy/                 Installers, Bicep/ARM templates, setup scripts
├── src/
│   ├── fabric/             Notebooks, pipelines, lakehouses, Fabric workloads
│   ├── power-bi/           Semantic models and reports (PBIP/TMDL)
│   ├── azure/              Functions, Logic Apps, infrastructure
│   ├── power-platform/     Power Apps and Power Automate solutions
│   └── copilot/            Copilot Studio or declarative agents
├── sample-data/            Synthetic data only
└── tests/
```

Include only the `src/` folders the accelerator needs.

## Metadata

`accelerator.json` drives the catalog in the root README.

| Field | Description |
| --- | --- |
| `name` | Folder name of the accelerator. |
| `title` | Display name. |
| `sector` | `education`, `nonprofit` or another agreed sector. |
| `description` | One or two sentences describing the scenario. |
| `technologies` | Microsoft technologies used, for example `Microsoft Fabric`, `Power BI`. |
| `version` | Semantic version of the accelerator. |
| `owners` | GitHub handles or teams that maintain the accelerator. |

## Security

- Never commit secrets, keys, passwords, connection strings, tokens, tenant IDs, subscription IDs,
  workspace IDs or internal URLs.
- Prefer secretless authentication, such as managed identities and workspace identities.
- Request the least privilege needed and document every permission or API scope.
- Do not add a custom backend or external service without a documented need and security review.

## Data and privacy

- Sample data must be fully synthetic. Do not include real student, donor, staff or customer data.
- Document what personal data the accelerator processes once deployed and how customers can
  control it.
- Do not send telemetry to Microsoft. If telemetry is ever required, it must be documented with
  opt-out instructions and reviewed first.

## Third-party content

- Register every third-party package and list it, with its license, in `THIRD-PARTY-NOTICES.md`.
- Do not copy vendor documentation, schemas or code unless its license allows redistribution.
- Use third-party product names only to describe compatibility.

## Quality

- Document prerequisites, deployment steps, cost drivers and known limits.
- Provide repeatable validation steps or automated tests.
- Check user-facing experiences, such as apps and reports, for accessibility.
