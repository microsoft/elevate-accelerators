import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { Item, ItemJobInstance } from "../../clients/FabricPlatformTypes";
import {
  PIPELINE_POLL_TIMEOUT_MS,
  getPollingDelayMs,
  getPipelineRunPath,
  getPipelineRunUrl,
  isRefreshDisabled,
  isPipelineJobActive,
  isReportingDataReady,
  pipelineJobStatusLabel,
  resolveBoundItem,
} from "./educationService";
import {
  createArtifactPrefix,
  createInstanceFolderName,
  getManagedArtifacts,
  getManagedArtifactNames,
} from "./EducationSolutionItemDefinition";
import { extractPipelineNotebookIds } from "./instanceService";
import { getArtifactTypeIconPath } from "./ArtifactTypeIcon";

const workspaceId = "11111111-1111-1111-1111-111111111111";

function item(id: string, displayName: string, type: string): Item {
  return { id, displayName, type, workspaceId };
}

describe("education artifact ownership", () => {
  it("resolves only the expected item type", () => {
    const items = [item("gold", "EDU_GD", "Lakehouse")];
    assert.equal(resolveBoundItem(items, "gold", "Lakehouse")?.id, "gold");
    assert.equal(resolveBoundItem(items, "gold", "Notebook"), undefined);
  });
});

describe("Fabric artifact icons", () => {
  it("maps managed item types to the same local icon names used by Fabric", () => {
    assert.equal(getArtifactTypeIconPath("Lakehouse"), "/assets/icons/lakehouse_32_item.svg");
    assert.equal(getArtifactTypeIconPath("Notebook"), "/assets/icons/notebook_32_item.svg");
    assert.equal(getArtifactTypeIconPath("DataPipeline"), "/assets/icons/pipeline_32_item.svg");
    assert.equal(getArtifactTypeIconPath("Semantic model"), "/assets/icons/semantic_model_32_item.svg");
    assert.equal(getArtifactTypeIconPath("Report"), "/assets/icons/report_32_item.svg");
    assert.equal(getArtifactTypeIconPath("Files"), undefined);
  });
});

describe("education instance naming", () => {
  it("derives a safe folder and deterministic artifact names from the item name", () => {
    assert.equal(createInstanceFolderName("North / District: 2026"), "North _ District_ 2026");
    assert.equal(createArtifactPrefix("North / District: 2026"), "North_District_2026");
    assert.equal(
      getManagedArtifactNames("North_District_2026").processingPipeline,
      "North_District_2026_BR_GD_Processing",
    );
  });

  it("defines the complete thirteen-artifact package", () => {
    const artifacts = getManagedArtifacts("District");
    assert.equal(artifacts.length, 13);
    assert.equal(artifacts.filter((artifact) => artifact.type === "Lakehouse").length, 3);
    assert.equal(artifacts.filter((artifact) => artifact.type === "Notebook").length, 7);
    assert.equal(artifacts.filter((artifact) => artifact.type === "DataPipeline").length, 1);
    assert.equal(artifacts.filter((artifact) => artifact.type === "SemanticModel").length, 1);
    assert.equal(artifacts.filter((artifact) => artifact.type === "Report").length, 1);
  });

  it("rejects folder names reserved by Fabric", () => {
    assert.throws(() => createInstanceFolderName("recycled"), /cannot be used/);
    assert.throws(() => createArtifactPrefix("###"), /cannot produce/);
  });
});

describe("legacy instance migration", () => {
  it("extracts notebook ownership from the six pipeline activities", () => {
    const notebookIds = Array.from({ length: 6 }, (_, index) => `notebook-${index + 1}`);
    const payload = Buffer.from(JSON.stringify({
      properties: {
        activities: notebookIds.map((notebookId) => ({ typeProperties: { notebookId } })),
      },
    })).toString("base64");

    assert.deepEqual(extractPipelineNotebookIds({
      parts: [{ path: "pipeline-content.json", payload, payloadType: "InlineBase64" }],
    }), notebookIds);
  });

  it("rejects pipeline definitions that cannot prove all notebook IDs", () => {
    const payload = Buffer.from(JSON.stringify({ properties: { activities: [] } })).toString("base64");
    assert.throws(
      () => extractPipelineNotebookIds({
        parts: [{ path: "pipeline-content.json", payload, payloadType: "InlineBase64" }],
      }),
      /expected six activities/,
    );
  });
});

describe("pipeline polling", () => {
  it("allows an hour for cold-start orchestration runs", () => {
    assert.equal(PIPELINE_POLL_TIMEOUT_MS, 3_600_000);
  });

  it("honors Retry-After without exceeding the remaining deadline", () => {
    assert.equal(getPollingDelayMs(60, 120_000), 60_000);
    assert.equal(getPollingDelayMs(60, 4_000), 4_000);
  });
});

describe("pipeline run navigation", () => {
  it("builds the Fabric monitoring route for a job instance", () => {
    assert.equal(
      getPipelineRunPath("workspace-id", "pipeline-id", "job-id"),
      "/workloads/data-pipeline/monitoring/workspaces/workspace-id/pipelines/pipeline-id/job-id",
    );
  });

  it("builds an absolute Fabric URL for opening a run in a browser tab", () => {
    assert.equal(
      getPipelineRunUrl("workspace id", "pipeline/id", "job?id"),
      "https://app.fabric.microsoft.com/workloads/data-pipeline/monitoring/workspaces/workspace%20id"
        + "/pipelines/pipeline%2Fid/job%3Fid",
    );
  });
});

describe("ribbon operation state", () => {
  it("disables refresh while a deployment or pipeline run is active", () => {
    assert.equal(isRefreshDisabled(false, false), false);
    assert.equal(isRefreshDisabled(true, false), true);
    assert.equal(isRefreshDisabled(false, true), true);
  });

  it("recognizes queued and running Fabric pipeline jobs", () => {
    assert.equal(isPipelineJobActive("NotStarted"), true);
    assert.equal(isPipelineJobActive("InProgress"), true);
    assert.equal(isPipelineJobActive("Completed"), false);
    assert.equal(isPipelineJobActive("Failed"), false);
    assert.equal(isPipelineJobActive(undefined), false);
  });

  it("presents Fabric job states in user language", () => {
    assert.equal(pipelineJobStatusLabel(undefined), "Not run");
    assert.equal(pipelineJobStatusLabel("NotStarted"), "Queued");
    assert.equal(pipelineJobStatusLabel("InProgress"), "Running");
    assert.equal(pipelineJobStatusLabel("Completed"), "Completed");
  });
});

describe("reporting readiness", () => {
  const completedJob: ItemJobInstance = {
    id: "job-id",
    itemId: "pipeline-id",
    jobType: "Pipeline",
    invokeType: "Manual",
    status: "Completed",
    endTimeUtc: "2026-10-07T10:57:16.6233333",
  };

  it("requires a completed orchestration run and a later completed model refresh", () => {
    assert.equal(isReportingDataReady(undefined, undefined), false);
    assert.equal(isReportingDataReady(completedJob, undefined), false);
    assert.equal(isReportingDataReady(completedJob, {
      status: "Unknown",
      startTime: "2026-10-07T11:29:08.723Z",
    }), false);
    assert.equal(isReportingDataReady(completedJob, {
      status: "Completed",
      endTime: "2026-10-07T11:37:56.447Z",
    }), true);
  });

  it("rejects a successful refresh that predates the latest orchestration run", () => {
    assert.equal(isReportingDataReady(completedJob, {
      status: "Completed",
      endTime: "2026-10-07T10:00:00Z",
    }), false);
  });
});
