# Adding an accelerator

1. Open a **New accelerator** issue with the sector, name, scenario, technologies and at least two
   maintainers. Wait for maintainer agreement before you start.
2. Copy [`templates/accelerator`](../templates/accelerator/) to `<sector>/<accelerator-name>/`.
3. Fill in `accelerator.json` and the README.
4. Add only the `src/` technology folders you need and remove the rest.
5. Add synthetic sample data, deployment steps and validation steps.
6. Add the accelerator to the catalog table in the root [README](../README.md) and to
   [CODEOWNERS](../.github/CODEOWNERS).
7. Open a pull request and complete the checklist.

Follow [Accelerator standards](accelerator-standards.md) throughout.
