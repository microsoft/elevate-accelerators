# Elevate Accelerators

Elevate Accelerators is a Microsoft Elevate open-source collection of reusable solution accelerators for schools, universities and nonprofits. Each accelerator packages deployable assets for Microsoft Fabric, Power BI, Azure, Microsoft 365 and Copilot, such as data pipelines, notebooks, data models, reports, setup scripts, reference architectures and documentation. The goal is to help customers and partners move from pilot to production faster using proven patterns instead of building from scratch.

## Accelerators

| Accelerator | Sector | Technologies |
| --- | --- | --- |
| [Education analytics](education/education-analytics/) | Education | Microsoft Fabric, Power BI |

## Repository structure

```text
elevate-accelerators/
├── docs/          Standards and guidance for all accelerators
├── education/     Accelerators for schools and universities
├── nonprofit/     Accelerators for nonprofit organizations
└── shared/        Assets reused by two or more accelerators
```

Accelerators are grouped by sector. Each accelerator is self-contained and can be deployed on its own. Technologies are subfolders inside the accelerator, so one accelerator can combine Fabric, Power BI, Azure, Power Platform and Copilot.

## Get started

1. Pick an accelerator from the table above.
2. Read its README for the scenario, prerequisites, cost and limits.
3. Follow its deployment guide in your own tenant.

See [Getting started](docs/getting-started.md) for more detail. All sample data in this repository is synthetic.

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose and add accelerators.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
