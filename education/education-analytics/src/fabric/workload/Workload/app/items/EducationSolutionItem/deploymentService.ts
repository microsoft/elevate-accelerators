import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ItemClient } from "../../clients/ItemClient";
import { Item, ItemDefinition, ItemDefinitionPart } from "../../clients/FabricPlatformTypes";
import { OneLakeStorageClient } from "../../clients/OneLakeStorageClient";
import {
  EducationArtifactBinding,
  EducationSolutionInstance,
  getManagedArtifactNames,
} from "./EducationSolutionItemDefinition";
import { configureSemanticModelConnection } from "./reportingService";

export const EDUCATION_PACKAGE_VERSION = "0.5.0";
export const SAMPLE_REPORTING_PERIOD = { start: "2024-09-01", end: "2026-05-09" } as const;

export type DeploymentItemState = "pending" | "in-progress" | "created" | "updated" | "reused" | "failed";

export interface DeploymentItemProgress {
  name: string;
  type: "Lakehouse" | "Notebook" | "DataPipeline" | "SemanticModel" | "Report" | "Files";
  state: DeploymentItemState;
  message?: string;
}

export interface EducationDeploymentResult {
  artifacts: EducationArtifactBinding;
  items: Item[];
}

export interface EducationDeploymentRequest {
  workspaceId: string;
  instance: EducationSolutionInstance;
  artifacts: EducationArtifactBinding;
  includeSampleData: boolean;
}

export function deploymentStateLabel(state: DeploymentItemState): string {
  const labels: Record<DeploymentItemState, string> = {
    pending: "Pending",
    "in-progress": "Updating",
    created: "Created",
    updated: "Updated",
    reused: "Already present",
    failed: "Failed",
  };
  return labels[state];
}

export function isBlockingNameCollision(existingType: string, targetType: DeploymentItemProgress["type"]): boolean {
  const isLakehouseCompanion = targetType === "Lakehouse" && existingType === "SQLEndpoint";
  const isEnrichmentPair = (targetType === "Notebook" && existingType === "DataPipeline")
    || (targetType === "DataPipeline" && existingType === "Notebook");
  return existingType !== targetType && !isLakehouseCompanion && !isEnrichmentPair;
}

export function resolveManagedItem(
  workspaceItems: Item[],
  storedId: string | undefined,
  folderId: string,
  name: string,
  type: DeploymentItemProgress["type"],
): Item | undefined {
  const storedItem = storedId ? workspaceItems.find((item) => item.id === storedId) : undefined;
  if (storedItem && (storedItem.type !== type || storedItem.folderId !== folderId)) {
    throw new Error(`${name} is not the expected ${type} in the solution folder.`);
  }
  if (storedItem) return storedItem;
  return workspaceItems.find(
    (item) => item.folderId === folderId && item.displayName === name && item.type === type,
  );
}

export function isUnwantedBronzeCompanion(item: Pick<Item, "displayName" | "type">): boolean {
  return item.displayName === "EDU_Bronze_EventhouseEndpoint"
    && (item.type === "KQLDatabase" || item.type === "Eventhouse");
}

export function isLegacyEnrichmentPipeline(item: Pick<Item, "displayName" | "type">): boolean {
  return item.displayName === "EDU_SL_GD_Enrichment" && item.type === "DataPipeline";
}

interface NotebookDocument {
  metadata?: Record<string, any>;
  cells: Array<{
    cell_type: string;
    source: string[];
    metadata?: Record<string, any>;
  }>;
}

interface SampleDataManifest {
  tables: Array<{ path: string }>;
}

interface ReportingAssetManifest {
  semanticModel: string[];
  report: string[];
}

const SAMPLE_DATA_ASSET_ROOT = "/assets/deployment/sample-data";
const SAMPLE_DATA_LAKEHOUSE_ROOT = "Files/landing/education-analytics";
const SAMPLE_DATA_SOURCES = new Set(["PowerSchool", "Canvas", "Moodle", "NWEA"]);
const REPORTING_ASSET_ROOT = "/assets/deployment/reporting";

export function getSampleDataPaths(manifest: SampleDataManifest): string[] {
  if (!Array.isArray(manifest.tables) || manifest.tables.length === 0) {
    throw new Error("The sample-data manifest has no tables.");
  }
  const paths = manifest.tables.map((table) => table.path.replace(/\\/g, "/"));
  const invalidPath = paths.find((path) => {
    const segments = path.split("/");
    return segments.length !== 2
      || !SAMPLE_DATA_SOURCES.has(segments[0])
      || !/^[^/]+\.csv$/i.test(segments[1])
      || segments.some((segment) => segment === "." || segment === "..");
  });
  if (invalidPath) throw new Error(`The sample-data manifest contains an unsafe path: ${invalidPath}`);
  if (new Set(paths).size !== paths.length) throw new Error("The sample-data manifest contains duplicate paths.");
  return paths;
}

interface NotebookSpec {
  bindingKey?: keyof EducationArtifactBinding;
  name: string;
  assetName: string;
  defaultLakehouse: "bronze" | "silver" | "gold";
  knownLakehouses?: Array<"bronze" | "silver" | "gold">;
  replacements?: Record<string, string>;
  parameterValues?: Record<string, string>;
}

function createNotebookSpecs(artifactPrefix: string): NotebookSpec[] {
  const names = getManagedArtifactNames(artifactPrefix);
  const replacements = {
    "{SILVER_LAKEHOUSE_NAME}": names.silverLakehouse,
    "{GOLD_LAKEHOUSE_NAME}": names.goldLakehouse,
    "%run <EDU_Config>": `%run ${names.configNotebook}`,
    "EDU_BR_CreateSchema": names.bronzeSchemaNotebook,
    "EDU_SL_CreateSchema": names.silverSchemaNotebook,
  };
  return [
    { bindingKey: "bronzeSchemaNotebookId", name: names.bronzeSchemaNotebook, assetName: "EDU_BR_CreateSchema.ipynb", defaultLakehouse: "bronze", replacements },
    { bindingKey: "bronzeIngestionNotebookId", name: names.bronzeIngestionNotebook, assetName: "EDU_BR_Ingestion.ipynb", defaultLakehouse: "bronze", replacements },
    { bindingKey: "silverSchemaNotebookId", name: names.silverSchemaNotebook, assetName: "EDU_SL_CreateSchema.ipynb", defaultLakehouse: "silver", replacements },
    {
      bindingKey: "bronzeSilverNotebookId",
      name: names.bronzeSilverNotebook,
      assetName: "EDU_BR_SL_Transform.ipynb",
      defaultLakehouse: "silver",
      knownLakehouses: ["bronze"],
      replacements,
      parameterValues: { bronze_lakehouse_name: JSON.stringify(names.bronzeLakehouse) },
    },
    { bindingKey: "configNotebookId", name: names.configNotebook, assetName: "EDU_Config.ipynb", defaultLakehouse: "gold", replacements },
    { bindingKey: "goldSchemaNotebookId", name: names.goldSchemaNotebook, assetName: "EDU_GD_CreateSchema.ipynb", defaultLakehouse: "gold", replacements },
    {
      bindingKey: "enrichmentNotebookId",
      name: names.enrichmentNotebook,
      assetName: "EDU_SL_GD_Enrichment.ipynb",
      defaultLakehouse: "gold",
      knownLakehouses: ["silver"],
      replacements,
    },
  ];
}

const commonReplacements: Record<string, string> = {
  "{SILVER_LAKEHOUSE_NAME}": "EDU_SL",
  "{SILVER_SCHEMA_NAME}": "",
  "{GOLD_LAKEHOUSE_NAME}": "EDU_GD",
  "{GOLD_SCHEMA_NAME}": "",
  "%run <EDU_Config>": "%run EDU_Config",
};

function utf8ToBase64(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

function base64ToUtf8(value: string): string {
  const binary = atob(value);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export function readReportingPeriod(definition: ItemDefinition): { start: string; end: string } | undefined {
  const part = definition.parts.find((candidate) => candidate.path.endsWith(".ipynb"));
  if (!part) return undefined;
  const content = base64ToUtf8(part.payload);
  const start = content.match(/period_start\s*=\s*\\?["']([0-9]{4}-[0-9]{2}-[0-9]{2})\\?["']/)?.[1];
  const end = content.match(/period_end\s*=\s*\\?["']([0-9]{4}-[0-9]{2}-[0-9]{2})\\?["']/)?.[1];
  return start && end ? { start, end } : undefined;
}

export function selectReportingPeriod(
  preservedPeriod: { start: string; end: string } | undefined,
  includeSampleData: boolean,
): { start: string; end: string } | undefined {
  return preservedPeriod ?? (includeSampleData ? SAMPLE_REPORTING_PERIOD : undefined);
}

function definitionPart(path: string, value: unknown): ItemDefinitionPart {
  return {
    path,
    payload: utf8ToBase64(typeof value === "string" ? value : JSON.stringify(value)),
    payloadType: "InlineBase64",
  };
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

function binaryDefinitionPart(path: string, bytes: Uint8Array): ItemDefinitionPart {
  return { path, payload: bytesToBase64(bytes), payloadType: "InlineBase64" };
}

function tmdlString(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

export function prepareSemanticModelExpressions(
  source: string,
  sqlEndpoint: string,
  goldDatabase: string,
): string {
  const endpointPattern = /expression GoldSqlEndpoint = "[^"]*"/;
  const databasePattern = /expression GoldDatabase = "[^"]*"/;
  if (!endpointPattern.test(source) || !databasePattern.test(source)) {
    throw new Error("The semantic model parameters could not be located.");
  }
  return source
    .replace(endpointPattern, `expression GoldSqlEndpoint = "${tmdlString(sqlEndpoint)}"`)
    .replace(databasePattern, `expression GoldDatabase = "${tmdlString(goldDatabase)}"`);
}

export function prepareReportBinding(source: string, semanticModelId: string): string {
  const definition = JSON.parse(source);
  if (!definition.datasetReference) throw new Error("The report definition has no semantic model reference.");
  definition.datasetReference = {
    byConnection: { connectionString: `semanticmodelid=${semanticModelId}` },
  };
  return JSON.stringify(definition, null, 2);
}

export function prepareNotebook(
  source: NotebookDocument,
  workspaceId: string,
  lakehouses: Record<"bronze" | "silver" | "gold", Item>,
  spec: NotebookSpec,
): NotebookDocument {
  const notebook = structuredClone(source);
  notebook.metadata ??= {};
  const defaultLakehouse = lakehouses[spec.defaultLakehouse];
  const knownKeys = [spec.defaultLakehouse, ...(spec.knownLakehouses ?? [])];
  notebook.metadata.dependencies = {
    lakehouse: {
      default_lakehouse: defaultLakehouse.id,
      default_lakehouse_name: defaultLakehouse.displayName,
      default_lakehouse_workspace_id: workspaceId,
      known_lakehouses: [...new Set(knownKeys)].map((key) => ({ id: lakehouses[key].id })),
    },
  };
  notebook.metadata.kernel_info = { name: "synapse_pyspark" };
  notebook.metadata.kernelspec = { display_name: "synapse_pyspark", name: "synapse_pyspark" };
  notebook.metadata.language_info = { name: "python" };
  notebook.metadata.microsoft = { language: "python", language_group: "synapse_pyspark" };

  const replacements = { ...commonReplacements, ...(spec.replacements ?? {}) };
  notebook.cells.forEach((cell) => {
    if (cell.cell_type !== "code") return;
    cell.metadata ??= {};
    cell.source = cell.source.map((sourceLine) => {
      let line = sourceLine;
      Object.entries(replacements).forEach(([token, replacement]) => {
        line = line.split(token).join(replacement);
      });
      return line;
    });
  });

  const parameterCell = notebook.cells.find(
    (cell) => cell.cell_type === "code" && cell.source.join("\n").startsWith("# Deployment parameters"),
  );
  if (!parameterCell) throw new Error(`${spec.name} has no deployment parameters cell.`);
  parameterCell.metadata ??= {};
  parameterCell.metadata.tags = ["parameters"];

  Object.entries(spec.parameterValues ?? {}).forEach(([parameterName, value]) => {
    const expression = new RegExp(`^${parameterName}\\s*=`);
    let found = false;
    parameterCell.source = parameterCell.source.map((line) => {
      if (!expression.test(line)) return line;
      found = true;
      return `${parameterName} = ${value}\n`;
    });
    if (!found) throw new Error(`${spec.name} is missing parameter ${parameterName}.`);
  });

  return notebook;
}

export function preparePipeline(source: any, replacements: Record<string, string>): any {
  let text = JSON.stringify(source);
  Object.entries(replacements).forEach(([token, value]) => {
    text = text.split(token).join(value);
  });
  const pipeline = JSON.parse(text);
  const activities = pipeline?.properties?.activities;
  if (!Array.isArray(activities) || activities.length !== 6 || pipeline.properties.concurrency !== 1) {
    throw new Error("The processing pipeline must contain six ordered activities with concurrency 1.");
  }
  activities.forEach((activity: any, index: number) => {
    if (index === 0 && activity.dependsOn?.length !== 0) throw new Error("The first pipeline activity must have no dependency.");
    if (index > 0) {
      const dependency = activity.dependsOn?.[0];
      if (activity.dependsOn?.length !== 1
        || dependency?.activity !== activities[index - 1].name
        || !dependency?.dependencyConditions?.includes("Succeeded")) {
        throw new Error(`Pipeline activity ${activity.name} must depend on the previous activity succeeding.`);
      }
    }
    if (!/^[0-9a-f-]{36}$/i.test(activity.typeProperties?.notebookId ?? "")) {
      throw new Error(`Pipeline activity ${activity.name} has an unresolved notebook ID.`);
    }
  });
  return pipeline;
}

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Could not load deployment asset ${path}: HTTP ${response.status}.`);
  return response.json() as Promise<T>;
}

async function loadBytes(path: string): Promise<Uint8Array> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Could not load deployment asset ${path}: HTTP ${response.status}.`);
  return new Uint8Array(await response.arrayBuffer());
}

async function loadReportingDefinition(
  assetFolder: "semantic-model" | "report",
  paths: string[],
  format: "TMDL" | "PBIR",
  transform?: (path: string, text: string) => string | undefined,
): Promise<ItemDefinition> {
  const parts = await Promise.all(paths.map(async (partPath) => {
    const bytes = await loadBytes(`${REPORTING_ASSET_ROOT}/${assetFolder}/${partPath}`);
    const transformed = transform?.(partPath, new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return transformed === undefined
      ? binaryDefinitionPart(partPath, bytes)
      : definitionPart(partPath, transformed);
  }));
  return { format, parts };
}

export async function deployEducationPackage(
  workloadClient: WorkloadClientAPI,
  request: EducationDeploymentRequest,
  onProgress: (progress: DeploymentItemProgress) => void,
): Promise<EducationDeploymentResult> {
  const { workspaceId, instance, artifacts: currentArtifacts, includeSampleData } = request;
  if (!instance.folderId) throw new Error("The Education solution folder must be saved before deployment.");
  const client = new ItemClient(workloadClient);
  const allWorkspaceItems = await client.getAllItems(workspaceId);
  const folderItems = allWorkspaceItems.filter((item) => item.folderId === instance.folderId);
  const deployedItems: Item[] = [];
  const artifacts: EducationArtifactBinding = { ...currentArtifacts };
  const names = getManagedArtifactNames(instance.artifactPrefix);

  async function removeUnwantedBronzeCompanions(): Promise<void> {
    const unwantedName = `${names.bronzeLakehouse}_EventhouseEndpoint`;
    const unwantedItems = (await client.getAllItems(workspaceId))
      .filter((item) => item.folderId === instance.folderId
        && item.displayName === unwantedName
        && (item.type === "KQLDatabase" || item.type === "Eventhouse"))
      .sort((left, right) => (left.type === "KQLDatabase" ? -1 : 1) - (right.type === "KQLDatabase" ? -1 : 1));
    for (const item of unwantedItems) {
      await client.deleteItem(workspaceId, item.id);
      const cachedIndex = folderItems.findIndex((candidate) => candidate.id === item.id);
      if (cachedIndex >= 0) folderItems.splice(cachedIndex, 1);
    }
  }

  async function removeLegacyPipeline(): Promise<void> {
    const legacyPipelines = (await client.getAllItems(workspaceId)).filter(
      (item) => item.folderId === instance.folderId
        && item.displayName === names.enrichmentNotebook
        && item.type === "DataPipeline"
        && item.id !== artifacts.processingPipelineId,
    );
    for (const item of legacyPipelines) {
      await client.deleteItem(workspaceId, item.id);
      const cachedIndex = folderItems.findIndex((candidate) => candidate.id === item.id);
      if (cachedIndex >= 0) folderItems.splice(cachedIndex, 1);
    }
  }

  async function deploySampleData(bronzeLakehouse: Item): Promise<void> {
    const progress: DeploymentItemProgress = {
      name: "Bronze sample data",
      type: "Files",
      state: "in-progress",
    };
    onProgress(progress);
    try {
      const manifestBytes = await loadBytes(`${SAMPLE_DATA_ASSET_ROOT}/manifest.json`);
      const manifestText = new TextDecoder("utf-8", { fatal: true }).decode(manifestBytes);
      const manifest = JSON.parse(manifestText) as SampleDataManifest;
      const paths = getSampleDataPaths(manifest);
      const storage = new OneLakeStorageClient(workloadClient).createItemWrapper({
        workspaceId,
        id: bronzeLakehouse.id,
      });
      await storage.createDirectory("Files/landing");
      await storage.createDirectory(SAMPLE_DATA_LAKEHOUSE_ROOT);
      for (const source of SAMPLE_DATA_SOURCES) {
        await storage.createDirectory(`${SAMPLE_DATA_LAKEHOUSE_ROOT}/${source}`);
      }
      await storage.writeFileAsBytes(`${SAMPLE_DATA_LAKEHOUSE_ROOT}/manifest.json`, manifestBytes);
      for (const path of paths) {
        const content = await loadBytes(`${SAMPLE_DATA_ASSET_ROOT}/${path}`);
        await storage.writeFileAsBytes(`${SAMPLE_DATA_LAKEHOUSE_ROOT}/${path}`, content);
      }
      onProgress({ ...progress, state: "updated", message: `${paths.length} CSV files uploaded` });
    } catch (error) {
      onProgress({ ...progress, state: "failed", message: error instanceof Error ? error.message : String(error) });
      throw error;
    }
  }

  async function getGoldSqlEndpoint(goldLakehouse: Item): Promise<string> {
    for (let attempt = 1; attempt <= 40; attempt++) {
      const lakehouse = await client.getLakehouse(workspaceId, goldLakehouse.id);
      const sqlEndpoint = lakehouse.properties.sqlEndpointProperties;
      if (sqlEndpoint.provisioningStatus === "Success" && sqlEndpoint.connectionString) {
        return sqlEndpoint.connectionString;
      }
      if (sqlEndpoint.provisioningStatus === "Failed") {
        throw new Error(`The SQL endpoint for ${goldLakehouse.displayName} failed to provision.`);
      }
      await new Promise((resolve) => window.setTimeout(resolve, 5000));
    }
    throw new Error(`The SQL endpoint for ${goldLakehouse.displayName} is still provisioning.`);
  }

  async function ensureItem(
    bindingKey: keyof EducationArtifactBinding,
    name: string,
    type: DeploymentItemProgress["type"],
    definition?: ItemDefinition,
  ): Promise<Item> {
    onProgress({ name, type, state: "in-progress" });
    try {
      const sameName = folderItems.filter((item) => item.displayName === name);
      const collision = sameName.find((item) => isBlockingNameCollision(item.type, type));
      if (collision) throw new Error(`${name} already exists as ${collision.type}; expected ${type}.`);

      let item = resolveManagedItem(
        allWorkspaceItems,
        artifacts[bindingKey],
        instance.folderId,
        name,
        type,
      );
      if (!item) {
        item = await client.createItemAndWait(workspaceId, {
          displayName: name,
          type,
          folderId: instance.folderId,
          description: `Managed by Education Analytics package ${EDUCATION_PACKAGE_VERSION}`,
          definition,
        });
        folderItems.push(item);
        allWorkspaceItems.push(item);
        onProgress({ name, type, state: "created" });
      } else if (definition) {
        if (item.displayName !== name) item = await client.updateItem(workspaceId, item.id, { displayName: name });
        await client.updateItemDefinitionAndWait(workspaceId, item.id, { definition });
        onProgress({ name, type, state: "updated" });
      } else {
        if (item.displayName !== name) item = await client.updateItem(workspaceId, item.id, { displayName: name });
        onProgress({ name, type, state: "reused" });
      }
      artifacts[bindingKey] = item.id;
      deployedItems.push(item);
      return item;
    } catch (error) {
      onProgress({ name, type, state: "failed", message: error instanceof Error ? error.message : String(error) });
      throw error;
    }
  }

  try {
    const bronze = await ensureItem("bronzeLakehouseId", names.bronzeLakehouse, "Lakehouse");
    const silver = await ensureItem("silverLakehouseId", names.silverLakehouse, "Lakehouse");
    const gold = await ensureItem("goldLakehouseId", names.goldLakehouse, "Lakehouse");
    await removeUnwantedBronzeCompanions();
    if (includeSampleData) await deploySampleData(bronze);
    const lakehouses = { bronze, silver, gold };
    const notebooks = new Map<string, Item>();

    const existingEnrichment = artifacts.enrichmentNotebookId
      ? allWorkspaceItems.find((candidate) => candidate.id === artifacts.enrichmentNotebookId
        && candidate.type === "Notebook" && candidate.folderId === instance.folderId)
      : folderItems.find((candidate) => candidate.displayName === names.enrichmentNotebook && candidate.type === "Notebook");
    let preservedPeriod: { start: string; end: string } | undefined;
    if (existingEnrichment) {
      const existingDefinition = await client.getItemDefinitionResolved(workspaceId, existingEnrichment.id, "ipynb");
      preservedPeriod = readReportingPeriod(existingDefinition.definition);
    }
    const reportingPeriod = selectReportingPeriod(preservedPeriod, includeSampleData);

    const notebookSpecs = createNotebookSpecs(instance.artifactPrefix);
    for (const spec of notebookSpecs) {
      const source = await loadJson<NotebookDocument>(`/assets/deployment/notebooks/${spec.assetName}`);
      const effectiveSpec = spec.name === names.enrichmentNotebook && reportingPeriod
        ? {
            ...spec,
            replacements: {
              ...spec.replacements,
              "{PERIOD_START}": reportingPeriod.start,
              "{PERIOD_END}": reportingPeriod.end,
            },
          }
        : spec;
      const prepared = prepareNotebook(source, workspaceId, lakehouses, effectiveSpec);
      const item = await ensureItem(spec.bindingKey!, spec.name, "Notebook", {
        format: "ipynb",
        parts: [definitionPart("notebook-content.ipynb", prepared)],
      });
      notebooks.set(spec.name, item);
    }

    const pipelineSource = await loadJson<any>("/assets/deployment/pipelines/EDU_BR_GD_Processing.json");
    const pipelineDefinition = preparePipeline(pipelineSource, {
      "{WORKSPACE_ID}": workspaceId,
      "{BRONZE_CREATE_SCHEMA_NOTEBOOK_ID}": notebooks.get(names.bronzeSchemaNotebook)!.id,
      "{BRONZE_INGESTION_NOTEBOOK_ID}": notebooks.get(names.bronzeIngestionNotebook)!.id,
      "{SILVER_CREATE_SCHEMA_NOTEBOOK_ID}": notebooks.get(names.silverSchemaNotebook)!.id,
      "{BRONZE_TO_SILVER_NOTEBOOK_ID}": notebooks.get(names.bronzeSilverNotebook)!.id,
      "{GOLD_CREATE_SCHEMA_NOTEBOOK_ID}": notebooks.get(names.goldSchemaNotebook)!.id,
      "{SILVER_TO_GOLD_ENRICHMENT_NOTEBOOK_ID}": notebooks.get(names.enrichmentNotebook)!.id,
    });
    await ensureItem("processingPipelineId", names.processingPipeline, "DataPipeline", {
      parts: [definitionPart("pipeline-content.json", pipelineDefinition)],
    });
    await removeLegacyPipeline();

    const reportingManifest = await loadJson<ReportingAssetManifest>(`${REPORTING_ASSET_ROOT}/manifest.json`);
    const sqlEndpoint = await getGoldSqlEndpoint(gold);
    const semanticModelDefinition = await loadReportingDefinition(
      "semantic-model",
      reportingManifest.semanticModel,
      "TMDL",
      (partPath, source) => partPath === "definition/expressions.tmdl"
        ? prepareSemanticModelExpressions(source, sqlEndpoint, gold.displayName)
        : undefined,
    );
    const semanticModel = await ensureItem(
      "semanticModelId",
      names.semanticModel,
      "SemanticModel",
      semanticModelDefinition,
    );
    await configureSemanticModelConnection(
      workloadClient,
      workspaceId,
      semanticModel.id,
      // Connection names are unique across the tenant, so the workspace keeps them apart.
      `${names.goldLakehouse}_SQL (${workspaceId})`,
      sqlEndpoint,
      gold.displayName,
    );
    const reportDefinition = await loadReportingDefinition(
      "report",
      reportingManifest.report,
      "PBIR",
      (partPath, source) => partPath === "definition.pbir"
        ? prepareReportBinding(source, semanticModel.id)
        : undefined,
    );
    await ensureItem("reportId", names.report, "Report", reportDefinition);

    return {
      artifacts: { ...artifacts, enrichmentPipelineId: undefined },
      items: deployedItems,
    };
  } catch (error) {
    throw error;
  }
}
