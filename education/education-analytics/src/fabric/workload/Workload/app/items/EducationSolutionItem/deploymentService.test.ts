import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { Item } from "../../clients/FabricPlatformTypes";
import {
  isBlockingNameCollision,
  deploymentStateLabel,
  isLegacyEnrichmentPipeline,
  isUnwantedBronzeCompanion,
  getSampleDataPaths,
  resolveManagedItem,
  prepareNotebook,
  preparePipeline,
  prepareReportBinding,
  prepareSemanticModelExpressions,
  readReportingPeriod,
  selectReportingPeriod,
} from "./deploymentService";
import { awaitSemanticModelRefresh, isReusableWorkspaceIdentityConnection } from "./reportingService";

const workspaceId = "11111111-1111-1111-1111-111111111111";
const lakehouses: Record<"bronze" | "silver" | "gold", Item> = {
  bronze: { id: "bronze-id", displayName: "EDU_Bronze", type: "Lakehouse", workspaceId },
  silver: { id: "silver-id", displayName: "EDU_SL", type: "Lakehouse", workspaceId },
  gold: { id: "gold-id", displayName: "EDU_GD", type: "Lakehouse", workspaceId },
};

function notebook(lines: string[]) {
  return {
    metadata: {},
    cells: [
      { cell_type: "code", source: ["# Deployment parameters\n", ...lines], metadata: {} },
      { cell_type: "code", source: ["%run <EDU_Config>\n", "gold = '{GOLD_LAKEHOUSE_NAME}'\n"], metadata: {} },
    ],
  };
}

describe("prepareNotebook", () => {
  it("injects default and known Lakehouse dependencies", () => {
    const prepared = prepareNotebook(notebook(["bronze_lakehouse_name = ''\n"]), workspaceId, lakehouses, {
      name: "EDU_BR_SL_Transform",
      assetName: "EDU_BR_SL_Transform.ipynb",
      defaultLakehouse: "silver",
      knownLakehouses: ["bronze"],
      parameterValues: { bronze_lakehouse_name: '"EDU_Bronze"' },
    });
    const dependency = prepared.metadata?.dependencies.lakehouse;
    assert.equal(dependency.default_lakehouse, "silver-id");
    assert.deepEqual(dependency.known_lakehouses, [{ id: "silver-id" }, { id: "bronze-id" }]);
    assert.equal(prepared.cells[0].source[1], 'bronze_lakehouse_name = "EDU_Bronze"\n');
  });

  it("replaces environment placeholders but leaves reporting dates unset", () => {
    const prepared = prepareNotebook(notebook(["period_start = '{PERIOD_START}'\n"]), workspaceId, lakehouses, {
      name: "EDU_SL_GD_Enrichment",
      assetName: "EDU_SL_GD_Enrichment.ipynb",
      defaultLakehouse: "gold",
      knownLakehouses: ["silver"],
    });
    assert.equal(prepared.cells[1].source[0], "%run EDU_Config\n");
    assert.equal(prepared.cells[1].source[1], "gold = 'EDU_GD'\n");
    assert.equal(prepared.cells[0].source[1], "period_start = '{PERIOD_START}'\n");
  });
});

describe("preparePipeline", () => {
  it("substitutes workspace and notebook IDs", () => {
    const names = ["Bronze schema", "Bronze ingestion", "Silver schema", "Silver transform", "Gold schema", "Gold enrichment"];
    const tokens = ["{BRONZE_CREATE_SCHEMA_NOTEBOOK_ID}", "{BRONZE_INGESTION_NOTEBOOK_ID}", "{SILVER_CREATE_SCHEMA_NOTEBOOK_ID}", "{BRONZE_TO_SILVER_NOTEBOOK_ID}", "{GOLD_CREATE_SCHEMA_NOTEBOOK_ID}", "{SILVER_TO_GOLD_ENRICHMENT_NOTEBOOK_ID}"];
    const source = {
      properties: {
        concurrency: 1,
        activities: names.map((name, index) => ({
          name,
          dependsOn: index === 0 ? [] : [{ activity: names[index - 1], dependencyConditions: ["Succeeded"] }],
          typeProperties: { workspaceId: "{WORKSPACE_ID}", notebookId: tokens[index] },
        })),
      },
    };
    const ids = ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000003", "00000000-0000-0000-0000-000000000004", "00000000-0000-0000-0000-000000000005", "00000000-0000-0000-0000-000000000006"];
    const prepared = preparePipeline(source, Object.fromEntries([
      ["{WORKSPACE_ID}", workspaceId],
      ...tokens.map((token, index) => [token, ids[index]]),
    ]));
    assert.equal(prepared.properties.activities[0].typeProperties.workspaceId, workspaceId);
    assert.deepEqual(prepared.properties.activities.map((activity: any) => activity.typeProperties.notebookId), ids);
  });

  it("rejects an unsafe pipeline shape", () => {
    assert.throws(() => preparePipeline({ properties: { concurrency: 2, activities: [] } }, {}));
  });
});

describe("reporting definitions", () => {
  it("binds semantic model parameters to the owned Gold Lakehouse", () => {
    const source = 'expression GoldSqlEndpoint = "" meta []\nexpression GoldDatabase = "EDU_GD" meta []';
    const prepared = prepareSemanticModelExpressions(source, "server.fabric.microsoft.com", "District_GD");
    assert.match(prepared, /GoldSqlEndpoint = "server\.fabric\.microsoft\.com"/);
    assert.match(prepared, /GoldDatabase = "District_GD"/);
  });

  it("rebinds the report to the deployed semantic model ID", () => {
    const prepared = JSON.parse(prepareReportBinding(JSON.stringify({
      version: "4.0",
      datasetReference: { byPath: { path: "../EducationAnalytics.SemanticModel" } },
    }), "11111111-2222-3333-4444-555555555555"));
    assert.deepEqual(prepared.datasetReference, {
      byConnection: { connectionString: "semanticmodelid=11111111-2222-3333-4444-555555555555" },
    });
  });
});

describe("semantic model refresh", () => {
  it("waits for the submitted refresh to complete", async () => {
    let requestCount = 0;
    await awaitSemanticModelRefresh(async () => {
      requestCount++;
      return [{ requestId: "refresh-1", status: requestCount === 1 ? "Unknown" : "Completed" }];
    }, "refresh-1", new Set(), async (): Promise<void> => undefined);
    assert.equal(requestCount, 2);
  });

  it("does not mistake a previous completed refresh for a new one when the response header is hidden", async () => {
    let requestCount = 0;
    await awaitSemanticModelRefresh(async () => {
      requestCount++;
      return requestCount === 1
        ? [{ requestId: "previous", status: "Completed" }]
        : [{ requestId: "new", status: "Completed" }, { requestId: "previous", status: "Completed" }];
    }, null, new Set(["previous"]), async (): Promise<void> => undefined);
    assert.equal(requestCount, 2);
  });

  it("includes Power BI processing details when refresh fails", async () => {
    await assert.rejects(
      awaitSemanticModelRefresh(
        async () => [{ requestId: "refresh-1", status: "Failed", serviceExceptionJson: "duplicate key" }],
        "refresh-1",
      ),
      /duplicate key/,
    );
  });

  it("reports a disabled refresh as a terminal failure", async () => {
    await assert.rejects(
      awaitSemanticModelRefresh(async () => [{ requestId: "refresh-1", status: "Disabled" }], "refresh-1"),
      /refresh disabled/,
    );
  });
});

describe("semantic model connection", () => {
  const connection = {
    id: "connection-id",
    displayName: "Gold SQL",
    connectivityType: "ShareableCloud" as const,
    connectionDetails: { type: "SQL", path: "server;database" },
    privacyLevel: "Organizational" as const,
    credentialDetails: {
      credentialType: "WorkspaceIdentity",
      singleSignOnType: "None" as const,
      connectionEncryption: "Encrypted" as const,
      skipTestConnection: false,
    },
  };

  it("reuses only a shareable workspace-identity SQL connection", () => {
    assert.equal(isReusableWorkspaceIdentityConnection(connection, "SERVER;DATABASE"), true);
    assert.equal(isReusableWorkspaceIdentityConnection({ ...connection, connectivityType: "PersonalCloud" }, "server;database"), false);
    assert.equal(isReusableWorkspaceIdentityConnection({
      ...connection,
      credentialDetails: { ...connection.credentialDetails, credentialType: "OAuth2" },
    }, "server;database"), false);
  });
});

describe("readReportingPeriod", () => {
  it("reads configured dates from an existing ipynb definition", () => {
    const payload = Buffer.from(JSON.stringify(notebook([
      'period_start = "2025-09-01"\n',
      'period_end = "2026-05-09"\n',
    ])), "utf8").toString("base64");
    const period = readReportingPeriod({
      format: "ipynb",
      parts: [{ path: "notebook-content.ipynb", payload, payloadType: "InlineBase64" }],
    });
    assert.deepEqual(period, { start: "2025-09-01", end: "2026-05-09" });
  });
});

describe("selectReportingPeriod", () => {
  it("uses sample bounds only for a fresh sample-data deployment", () => {
    assert.deepEqual(selectReportingPeriod(undefined, true), { start: "2024-09-01", end: "2026-05-09" });
    assert.equal(selectReportingPeriod(undefined, false), undefined);
  });

  it("preserves an existing configured period", () => {
    const existing = { start: "2024-08-15", end: "2025-06-01" };
    assert.deepEqual(selectReportingPeriod(existing, true), existing);
  });
});

describe("deployment collisions", () => {
  it("ignores the SQL endpoint Fabric creates beside a Lakehouse", () => {
    assert.equal(isBlockingNameCollision("SQLEndpoint", "Lakehouse"), false);
    assert.equal(isBlockingNameCollision("DataPipeline", "Notebook"), false);
    assert.equal(isBlockingNameCollision("Notebook", "DataPipeline"), false);
    assert.equal(isBlockingNameCollision("Notebook", "Lakehouse"), true);
  });
});

describe("managed item ownership", () => {
  const workspaceId = "11111111-1111-1111-1111-111111111111";
  const managed = { id: "managed", displayName: "District_Bronze", type: "Lakehouse", workspaceId, folderId: "folder-a" };
  const other = { id: "other", displayName: "District_Bronze", type: "Lakehouse", workspaceId, folderId: "folder-b" };

  it("resolves a stored ID only inside the owned folder", () => {
    assert.equal(resolveManagedItem([managed, other], "managed", "folder-a", "District_Bronze", "Lakehouse")?.id, "managed");
    assert.throws(
      () => resolveManagedItem([managed, other], "other", "folder-a", "District_Bronze", "Lakehouse"),
      /solution folder/,
    );
  });

  it("does not adopt an equal name from another folder", () => {
    assert.equal(resolveManagedItem([other], undefined, "folder-a", "District_Bronze", "Lakehouse"), undefined);
  });

  it("recovers from a stale stored ID using the owned folder", () => {
    assert.equal(
      resolveManagedItem([managed, other], "deleted", "folder-a", "District_Bronze", "Lakehouse")?.id,
      "managed",
    );
    assert.equal(resolveManagedItem([], "deleted", "folder-a", "District_Bronze", "Lakehouse"), undefined);
  });
});

describe("sample data manifest", () => {
  it("accepts source-qualified CSV paths", () => {
    assert.deepEqual(getSampleDataPaths({ tables: [
      { path: "PowerSchool/students.csv" },
      { path: "Canvas/submissions.csv" },
    ] }), ["PowerSchool/students.csv", "Canvas/submissions.csv"]);
  });

  it("rejects traversal, unknown sources, and duplicate paths", () => {
    assert.throws(() => getSampleDataPaths({ tables: [{ path: "../secret.csv" }] }), /unsafe path/);
    assert.throws(() => getSampleDataPaths({ tables: [{ path: "Other/data.csv" }] }), /unsafe path/);
    assert.throws(() => getSampleDataPaths({ tables: [
      { path: "NWEA/results.csv" },
      { path: "NWEA/results.csv" },
    ] }), /duplicate paths/);
  });
});

describe("Bronze companion cleanup", () => {
  it("removes only the generated Eventhouse endpoint pair", () => {
    assert.equal(isUnwantedBronzeCompanion({ displayName: "EDU_Bronze_EventhouseEndpoint", type: "KQLDatabase" }), true);
    assert.equal(isUnwantedBronzeCompanion({ displayName: "EDU_Bronze_EventhouseEndpoint", type: "Eventhouse" }), true);
    assert.equal(isUnwantedBronzeCompanion({ displayName: "EDU_Bronze", type: "Lakehouse" }), false);
    assert.equal(isUnwantedBronzeCompanion({ displayName: "EDU_Bronze", type: "SQLEndpoint" }), false);
    assert.equal(isUnwantedBronzeCompanion({ displayName: "DistrictEventhouse", type: "Eventhouse" }), false);
  });
});

describe("legacy pipeline cleanup", () => {
  it("targets only the retired managed enrichment pipeline", () => {
    assert.equal(isLegacyEnrichmentPipeline({ displayName: "EDU_SL_GD_Enrichment", type: "DataPipeline" }), true);
    assert.equal(isLegacyEnrichmentPipeline({ displayName: "EDU_SL_GD_Enrichment", type: "Notebook" }), false);
    assert.equal(isLegacyEnrichmentPipeline({ displayName: "EDU_BR_GD_Processing", type: "DataPipeline" }), false);
  });
});

describe("deployment progress labels", () => {
  it("presents internal deployment states in user language", () => {
    assert.equal(deploymentStateLabel("in-progress"), "Updating");
    assert.equal(deploymentStateLabel("reused"), "Already present");
    assert.equal(deploymentStateLabel("updated"), "Updated");
  });
});
