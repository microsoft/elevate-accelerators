import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { FolderClient } from "../../clients/FolderClient";
import { Item, ItemDefinition } from "../../clients/FabricPlatformTypes";
import { ItemClient } from "../../clients/ItemClient";
import {
  createArtifactPrefix,
  createInstanceFolderName,
  EducationArtifactBinding,
  EducationSolutionInstance,
  EducationSolutionItemDefinition,
  getManagedArtifactNames,
  getRequiredArtifacts,
  LEGACY_ARTIFACT_PREFIX,
} from "./EducationSolutionItemDefinition";

function base64ToUtf8(value: string): string {
  const binary = atob(value);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export function extractPipelineNotebookIds(definition: ItemDefinition): string[] {
  const part = definition.parts.find((candidate) => candidate.path.endsWith("pipeline-content.json"));
  if (!part) throw new Error("The legacy processing pipeline has no pipeline-content.json definition.");
  const pipeline = JSON.parse(base64ToUtf8(part.payload));
  const activities = pipeline?.properties?.activities;
  if (!Array.isArray(activities) || activities.length !== 6) {
    throw new Error("The legacy processing pipeline does not have the expected six activities.");
  }
  const notebookIds = activities.map((activity: any) => activity?.typeProperties?.notebookId);
  if (notebookIds.some((id: unknown) => typeof id !== "string" || !id)) {
    throw new Error("The legacy processing pipeline has an invalid notebook reference.");
  }
  return notebookIds;
}

export async function ensureEducationInstance(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  itemDisplayName: string,
  currentInstance: EducationSolutionInstance | undefined,
): Promise<EducationSolutionInstance> {
  const folders = new FolderClient(workloadClient);
  if (currentInstance?.folderId) {
    const folder = await folders.getFolder(workspaceId, currentInstance.folderId);
    return {
      ...currentInstance,
      folderName: folder.displayName,
    };
  }

  const folderName = createInstanceFolderName(itemDisplayName);
  const artifactPrefix = currentInstance?.artifactPrefix ?? createArtifactPrefix(itemDisplayName);
  const matchingFolders = (await folders.getDirectChildFolders(workspaceId))
    .filter((folder) => folder.displayName === folderName);
  if (matchingFolders.length > 0) {
    throw new Error(`A root folder named ${folderName} already exists and is not owned by this Education solution.`);
  }

  const folder = await folders.createFolder(workspaceId, { displayName: folderName });

  return {
    folderId: folder.id,
    folderName: folder.displayName,
    artifactPrefix,
  };
}

export async function migrateLegacyEducationInstance(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  itemDisplayName: string,
  definition: EducationSolutionItemDefinition,
): Promise<EducationSolutionItemDefinition> {
  if (definition.schemaVersion !== 1) return definition;

  const client = new ItemClient(workloadClient);
  const folders = new FolderClient(workloadClient);
  const workspaceItems = await client.getAllItems(workspaceId);
  const folderName = createInstanceFolderName(itemDisplayName);
  const matchingFolders = (await folders.getDirectChildFolders(workspaceId))
    .filter((folder) => folder.displayName === folderName);
  if (matchingFolders.length > 1) throw new Error(`More than one root folder is named ${folderName}.`);
  const existingFolder = matchingFolders[0];
  const isValidMigrationLocation = (item: Item) => !item.folderId || item.folderId === existingFolder?.id;
  const legacyNames = getManagedArtifactNames(LEGACY_ARTIFACT_PREFIX);
  const coreSpecs = getRequiredArtifacts(LEGACY_ARTIFACT_PREFIX);
  const coreItems = coreSpecs.map((spec) => {
    const id = definition.artifacts[spec.key];
    const item = id ? workspaceItems.find((candidate) => candidate.id === id) : undefined;
    if (!item || item.type !== spec.type || item.displayName !== spec.displayName || !isValidMigrationLocation(item)) {
      throw new Error(`Legacy artifact ${spec.displayName} could not be verified for migration.`);
    }
    return item;
  });

  const pipelineId = definition.artifacts.processingPipelineId!;
  const pipelineDefinition = await client.getItemDefinitionResolved(workspaceId, pipelineId);
  const notebookIds = extractPipelineNotebookIds(pipelineDefinition.definition);
  const migratedArtifacts: EducationArtifactBinding = { ...definition.artifacts };
  const notebookSpecs: Array<[keyof EducationArtifactBinding, string]> = [
    ["bronzeSchemaNotebookId", legacyNames.bronzeSchemaNotebook],
    ["bronzeIngestionNotebookId", legacyNames.bronzeIngestionNotebook],
    ["silverSchemaNotebookId", legacyNames.silverSchemaNotebook],
    ["bronzeSilverNotebookId", legacyNames.bronzeSilverNotebook],
    ["goldSchemaNotebookId", legacyNames.goldSchemaNotebook],
    ["enrichmentNotebookId", legacyNames.enrichmentNotebook],
  ];
  const notebookItems = notebookSpecs.map(([key, expectedName], index) => {
    const notebook = workspaceItems.find((candidate) => candidate.id === notebookIds[index]);
    if (!notebook || notebook.type !== "Notebook" || notebook.displayName !== expectedName || !isValidMigrationLocation(notebook)) {
      throw new Error(`Legacy notebook ${expectedName} could not be verified for migration.`);
    }
    migratedArtifacts[key] = notebook.id;
    return notebook;
  });

  const managedItems = [...coreItems, ...notebookItems];
  if (existingFolder && !managedItems.some((item) => item.folderId === existingFolder.id)) {
    throw new Error(`A root folder named ${folderName} already exists and is not owned by this Education solution.`);
  }
  const instance = existingFolder
    ? { folderId: existingFolder.id, folderName: existingFolder.displayName, artifactPrefix: createArtifactPrefix(itemDisplayName) }
    : await ensureEducationInstance(workloadClient, workspaceId, itemDisplayName, undefined);
  const itemsToMove = [...new Set(managedItems.filter((item) => item.folderId !== instance.folderId).map((item) => item.id))];
  if (itemsToMove.length > 0) {
    try {
      await client.bulkMoveItems(workspaceId, { items: itemsToMove, targetFolderId: instance.folderId });
    } catch (error) {
      if (!existingFolder && (await client.getItemsInFolder(workspaceId, instance.folderId!)).length === 0) {
        await folders.deleteFolder(workspaceId, instance.folderId!);
      }
      throw error;
    }
  }

  return {
    ...definition,
    schemaVersion: 2,
    workspaceId,
    instance,
    artifacts: { ...migratedArtifacts, enrichmentPipelineId: undefined },
  };
}
