import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { callAcquireFrontendAccessToken } from "../../clients/FabricAuthenticationService";
import { ConnectionClient } from "../../clients/ConnectionClient";
import { Connection } from "../../clients/FabricPlatformTypes";
import { WorkspaceClient } from "../../clients/WorkspaceClient";

const POWER_BI_SCOPE = "https://analysis.windows.net/powerbi/api/Dataset.ReadWrite.All";

export type SemanticModelRefresh = {
  requestId?: string;
  status?: string;
  startTime?: string;
  endTime?: string;
  serviceExceptionJson?: string;
};

export function isReusableWorkspaceIdentityConnection(connection: Connection, connectionPath: string): boolean {
  return connection.connectionDetails.type === "SQL"
    && connection.connectivityType === "ShareableCloud"
    && connection.credentialDetails.credentialType === "WorkspaceIdentity"
    && connection.connectionDetails.path.toLowerCase() === connectionPath.toLowerCase();
}

export async function awaitSemanticModelRefresh(
  getRefreshes: () => Promise<SemanticModelRefresh[]>,
  requestId: string | null,
  previousRequestIds: ReadonlySet<string> = new Set(),
  delay: () => Promise<void> = () => new Promise((resolve) => window.setTimeout(resolve, 5000)),
): Promise<void> {
  for (let attempt = 1; attempt <= 120; attempt++) {
    const refresh = (await getRefreshes()).find((entry) => requestId
      ? entry.requestId === requestId
      : Boolean(entry.requestId && !previousRequestIds.has(entry.requestId)));
    if (refresh?.status === "Completed") return;
    if (refresh?.status === "Failed" || refresh?.status === "Cancelled" || refresh?.status === "Disabled") {
      throw new Error(`Semantic model refresh ${refresh.status.toLowerCase()}. ${refresh.serviceExceptionJson ?? ""}`);
    }
    if (attempt < 120) await delay();
  }
  throw new Error("Semantic model refresh is still running after ten minutes.");
}

async function powerBiRequest(
  workloadClient: WorkloadClientAPI,
  path: string,
  method: "GET" | "POST",
  body?: unknown,
): Promise<Response> {
  const accessToken = await callAcquireFrontendAccessToken(workloadClient, POWER_BI_SCOPE);
  const response = await fetch(`https://api.powerbi.com/v1.0/myorg/${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken.token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Power BI API ${method} ${path} failed: HTTP ${response.status}. ${detail}`);
  }
  return response;
}

export async function getLatestSemanticModelRefresh(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  semanticModelId: string,
): Promise<SemanticModelRefresh | undefined> {
  const response = await powerBiRequest(
    workloadClient,
    `groups/${workspaceId}/datasets/${semanticModelId}/refreshes?$top=10`,
    "GET",
  );
  const body = await response.json();
  return (body.value as SemanticModelRefresh[] | undefined)
    ?.sort((left, right) => (right.startTime ?? "").localeCompare(left.startTime ?? ""))[0];
}

export async function configureSemanticModelConnection(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  semanticModelId: string,
  connectionName: string,
  sqlEndpoint: string,
  database: string,
): Promise<void> {
  const workspaceClient = new WorkspaceClient(workloadClient);
  const workspace = await workspaceClient.getWorkspace(workspaceId);
  const identity = workspace.workspaceIdentity ?? await workspaceClient.provisionWorkspaceIdentity(workspaceId);
  await workspaceClient.ensureWorkspaceIdentityViewer(workspaceId, identity);

  const connectionClient = new ConnectionClient(workloadClient);
  const connectionPath = `${sqlEndpoint};${database}`.toLowerCase();
  const existing = (await connectionClient.getAllConnections()).find(
    (connection) => isReusableWorkspaceIdentityConnection(connection, connectionPath),
  );
  const connection = existing ?? await connectionClient.createConnection({
    connectivityType: "ShareableCloud",
    displayName: connectionName,
    connectionDetails: {
      type: "SQL",
      creationMethod: "Sql",
      parameters: [
        { dataType: "Text", name: "server", value: sqlEndpoint },
        { dataType: "Text", name: "database", value: database },
      ],
    },
    privacyLevel: "Organizational",
    credentialDetails: {
      singleSignOnType: "None",
      connectionEncryption: "Encrypted",
      skipTestConnection: false,
      credentials: { credentialType: "WorkspaceIdentity" },
    },
  });

  await powerBiRequest(
    workloadClient,
    `groups/${workspaceId}/datasets/${semanticModelId}/Default.BindToGateway`,
    "POST",
    { gatewayObjectId: connection.gatewayId, datasourceObjectIds: [connection.id] },
  );
}

export async function refreshSemanticModel(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  semanticModelId: string,
): Promise<void> {
  const previousResponse = await powerBiRequest(
    workloadClient,
    `groups/${workspaceId}/datasets/${semanticModelId}/refreshes?$top=10`,
    "GET",
  );
  const previousBody = await previousResponse.json();
  const previousRequestIds = new Set<string>(
    (previousBody.value ?? []).flatMap((entry: SemanticModelRefresh) => entry.requestId ? [entry.requestId] : []),
  );
  const refreshResponse = await powerBiRequest(
    workloadClient,
    `groups/${workspaceId}/datasets/${semanticModelId}/refreshes`,
    "POST",
    { notifyOption: "NoNotification" },
  );
  const requestId = refreshResponse.headers.get("RequestId");
  await awaitSemanticModelRefresh(async () => {
    const response = await powerBiRequest(
      workloadClient,
      `groups/${workspaceId}/datasets/${semanticModelId}/refreshes?$top=10`,
      "GET",
    );
    const body = await response.json();
    return body.value ?? [];
  }, requestId, previousRequestIds);
}
