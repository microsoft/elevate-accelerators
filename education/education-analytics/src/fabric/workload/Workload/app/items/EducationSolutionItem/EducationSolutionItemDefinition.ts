export interface EducationArtifactBinding {
  bronzeLakehouseId?: string;
  silverLakehouseId?: string;
  goldLakehouseId?: string;
  bronzeSchemaNotebookId?: string;
  bronzeIngestionNotebookId?: string;
  silverSchemaNotebookId?: string;
  bronzeSilverNotebookId?: string;
  configNotebookId?: string;
  goldSchemaNotebookId?: string;
  enrichmentNotebookId?: string;
  processingPipelineId?: string;
  /** Legacy v0.2 binding retained so existing item definitions remain readable. */
  enrichmentPipelineId?: string;
  semanticModelId?: string;
  reportId?: string;
}

export interface EducationSolutionInstance {
  folderId?: string;
  folderName: string;
  artifactPrefix: string;
}

export interface EducationSolutionItemDefinition {
  schemaVersion: 1 | 2;
  workspaceId: string;
  artifacts: EducationArtifactBinding;
  instance?: EducationSolutionInstance;
  deployment?: {
    packageVersion: string;
    completedAtUtc: string;
  };
}

export const EMPTY_EDUCATION_DEFINITION: EducationSolutionItemDefinition = {
  schemaVersion: 2,
  workspaceId: "",
  artifacts: {},
};

export interface EducationArtifactSpec {
  key: keyof EducationArtifactBinding;
  displayName: string;
  type: string;
  layer: "Bronze" | "Silver" | "Gold" | "Flow" | "Reporting";
}

export function createInstanceFolderName(itemDisplayName: string): string {
  const cleaned = itemDisplayName
    .replace(/[\u0000-\u001f\u007f-\u009f~"#.&*:<>?/\\{|}]/g, "_")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 255);
  if (!cleaned || ["$recycle.bin", "recycled", "recycler"].includes(cleaned.toLowerCase())) {
    throw new Error("The Education item name cannot be used as a Fabric folder name.");
  }
  return cleaned;
}

export function createArtifactPrefix(itemDisplayName: string): string {
  const prefix = itemDisplayName
    .normalize("NFKD")
    .replace(/[^A-Za-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
  if (!prefix) throw new Error("The Education item name cannot produce a valid artifact prefix.");
  return prefix;
}

export function getRequiredArtifacts(artifactPrefix: string): ReadonlyArray<EducationArtifactSpec> {
  return [
    { key: "bronzeLakehouseId", displayName: `${artifactPrefix}_Bronze`, type: "Lakehouse", layer: "Bronze" },
    { key: "silverLakehouseId", displayName: `${artifactPrefix}_SL`, type: "Lakehouse", layer: "Silver" },
    { key: "goldLakehouseId", displayName: `${artifactPrefix}_GD`, type: "Lakehouse", layer: "Gold" },
    { key: "processingPipelineId", displayName: `${artifactPrefix}_BR_GD_Processing`, type: "DataPipeline", layer: "Flow" },
  ];
}

export function getManagedArtifacts(artifactPrefix: string): ReadonlyArray<EducationArtifactSpec> {
  const names = getManagedArtifactNames(artifactPrefix);
  return [
    { key: "bronzeLakehouseId", displayName: names.bronzeLakehouse, type: "Lakehouse", layer: "Bronze" },
    { key: "silverLakehouseId", displayName: names.silverLakehouse, type: "Lakehouse", layer: "Silver" },
    { key: "goldLakehouseId", displayName: names.goldLakehouse, type: "Lakehouse", layer: "Gold" },
    { key: "bronzeSchemaNotebookId", displayName: names.bronzeSchemaNotebook, type: "Notebook", layer: "Bronze" },
    { key: "bronzeIngestionNotebookId", displayName: names.bronzeIngestionNotebook, type: "Notebook", layer: "Bronze" },
    { key: "silverSchemaNotebookId", displayName: names.silverSchemaNotebook, type: "Notebook", layer: "Silver" },
    { key: "bronzeSilverNotebookId", displayName: names.bronzeSilverNotebook, type: "Notebook", layer: "Silver" },
    { key: "configNotebookId", displayName: names.configNotebook, type: "Notebook", layer: "Gold" },
    { key: "goldSchemaNotebookId", displayName: names.goldSchemaNotebook, type: "Notebook", layer: "Gold" },
    { key: "enrichmentNotebookId", displayName: names.enrichmentNotebook, type: "Notebook", layer: "Gold" },
    { key: "processingPipelineId", displayName: names.processingPipeline, type: "DataPipeline", layer: "Flow" },
    { key: "semanticModelId", displayName: names.semanticModel, type: "SemanticModel", layer: "Reporting" },
    { key: "reportId", displayName: names.report, type: "Report", layer: "Reporting" },
  ];
}

export interface EducationManagedArtifactNames {
  bronzeLakehouse: string;
  silverLakehouse: string;
  goldLakehouse: string;
  bronzeSchemaNotebook: string;
  bronzeIngestionNotebook: string;
  silverSchemaNotebook: string;
  bronzeSilverNotebook: string;
  configNotebook: string;
  goldSchemaNotebook: string;
  enrichmentNotebook: string;
  processingPipeline: string;
  semanticModel: string;
  report: string;
}

export function getManagedArtifactNames(artifactPrefix: string): EducationManagedArtifactNames {
  return {
    bronzeLakehouse: `${artifactPrefix}_Bronze`,
    silverLakehouse: `${artifactPrefix}_SL`,
    goldLakehouse: `${artifactPrefix}_GD`,
    bronzeSchemaNotebook: `${artifactPrefix}_BR_CreateSchema`,
    bronzeIngestionNotebook: `${artifactPrefix}_BR_Ingestion`,
    silverSchemaNotebook: `${artifactPrefix}_SL_CreateSchema`,
    bronzeSilverNotebook: `${artifactPrefix}_BR_SL_Transform`,
    configNotebook: `${artifactPrefix}_Config`,
    goldSchemaNotebook: `${artifactPrefix}_GD_CreateSchema`,
    enrichmentNotebook: `${artifactPrefix}_SL_GD_Enrichment`,
    processingPipeline: `${artifactPrefix}_BR_GD_Processing`,
    semanticModel: `${artifactPrefix}_Analytics`,
    report: `${artifactPrefix}_Insights`,
  };
}

export const LEGACY_ARTIFACT_PREFIX = "EDU";

export const OPTIONAL_ARTIFACTS: ReadonlyArray<{
  key: keyof EducationArtifactBinding;
  displayName: string;
  type: string;
}> = [
  { key: "semanticModelId", displayName: "EDU_Analytics", type: "SemanticModel" },
  { key: "reportId", displayName: "EDU_Insights", type: "Report" },
];