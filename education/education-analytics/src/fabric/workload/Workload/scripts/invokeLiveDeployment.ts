import { readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";

const token = process.env.FABRIC_TOKEN;
const workspaceId = process.env.FABRIC_WORKSPACE_ID;
const acceleratorRoot = process.env.ACCELERATOR_ROOT;
const folderId = process.env.EDUCATION_FOLDER_ID;
const folderName = process.env.EDUCATION_FOLDER_NAME;
const artifactPrefix = process.env.EDUCATION_ARTIFACT_PREFIX;
if (!token || !workspaceId || !acceleratorRoot || !folderId || !folderName || !artifactPrefix) {
  throw new Error("FABRIC_TOKEN, FABRIC_WORKSPACE_ID, ACCELERATOR_ROOT, EDUCATION_FOLDER_ID, EDUCATION_FOLDER_NAME and EDUCATION_ARTIFACT_PREFIX are required.");
}

Object.defineProperty(globalThis, "window", {
  configurable: true,
  value: { parent: {}, setTimeout },
});

const nativeFetch = globalThis.fetch;
async function listFiles(root: string, relative = ""): Promise<string[]> {
  const entries = await readdir(resolve(root, relative), { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const next = relative ? `${relative}/${entry.name}` : entry.name;
    if (entry.isDirectory()) return entry.name === ".pbi" ? [] : listFiles(root, next);
    return entry.name === ".platform" ? [] : [next];
  }));
  return files.flat().sort();
}

globalThis.fetch = async (input, init) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (url.startsWith("/assets/deployment/notebooks/")) {
    const name = url.substring(url.lastIndexOf("/") + 1);
    return new Response(await readFile(resolve(acceleratorRoot, "src", "fabric", "notebooks", name)), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (url === "/assets/deployment/pipelines/EDU_BR_GD_Processing.json") {
    return new Response(await readFile(resolve(acceleratorRoot, "src", "fabric", "pipelines", "EDU_BR_GD_Processing.DataPipeline", "pipeline-content.json")), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (url === "/assets/deployment/reporting/manifest.json") {
    const reportsRoot = resolve(acceleratorRoot, "src", "power-bi");
    return Response.json({
      semanticModel: await listFiles(resolve(reportsRoot, "EducationAnalytics.SemanticModel")),
      report: await listFiles(resolve(reportsRoot, "EducationAnalytics.Report")),
    });
  }
  const reportingMatch = url.match(/^\/assets\/deployment\/reporting\/(semantic-model|report)\/(.+)$/);
  if (reportingMatch) {
    const folder = reportingMatch[1] === "semantic-model"
      ? "EducationAnalytics.SemanticModel"
      : "EducationAnalytics.Report";
    return new Response(await readFile(resolve(acceleratorRoot, "src", "power-bi", folder, reportingMatch[2])));
  }
  return nativeFetch(input, init);
};

async function main() {
  const { deployEducationPackage } = await import("../app/items/EducationSolutionItem/deploymentService");
  const workloadClient = {
    auth: {
      acquireFrontendAccessToken: async () => ({ token }),
    },
  };

  const result = await deployEducationPackage(workloadClient as never, {
    workspaceId,
    instance: { folderId, folderName, artifactPrefix },
    artifacts: {},
    includeSampleData: process.env.EDUCATION_INCLUDE_SAMPLE_DATA === "true",
  }, (progress) => {
    console.log(`${progress.state.padEnd(11)} ${progress.type.padEnd(12)} ${progress.name}`);
  });

  console.log(JSON.stringify({
    artifacts: result.artifacts,
    deployedItemCount: result.items.length,
  }, null, 2));
}

void main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
