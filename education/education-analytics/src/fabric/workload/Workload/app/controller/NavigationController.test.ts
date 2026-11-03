import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getFrontendPath } from "./NavigationController";

describe("Fabric item navigation", () => {
  it("uses the Power BI datasets route for semantic models", () => {
    assert.equal(
      getFrontendPath("SemanticModel", "workspace-id", "semantic-model-id"),
      "/groups/workspace-id/datasets/semantic-model-id",
    );
  });

  it("keeps reports on the Power BI reports route", () => {
    assert.equal(
      getFrontendPath("Report", "workspace-id", "report-id"),
      "/groups/workspace-id/reports/report-id",
    );
  });
});
