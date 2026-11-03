import React, { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import {
  Button,
  Checkbox,
  MessageBar,
  MessageBarBody,
} from "@fluentui/react-components";
import {
  CheckmarkCircle20Filled,
  Open16Regular,
  Play20Regular,
  Warning20Filled,
} from "@fluentui/react-icons";
import { ContextProps, PageProps } from "../../App";
import { Item, ItemJobInstance } from "../../clients/FabricPlatformTypes";
import { ItemEditor } from "../../components/ItemEditor";
import {
  ItemWithDefinition,
  callGetItem,
  getWorkloadItem,
  saveWorkloadItem,
} from "../../controller/ItemCRUDController";
import { callNavigationOpenInNewBrowserTab, navigateToItem } from "../../controller/NavigationController";
import { callOpenSettings } from "../../controller/SettingsController";
import {
  createArtifactPrefix,
  createInstanceFolderName,
  EducationSolutionItemDefinition,
  EMPTY_EDUCATION_DEFINITION,
  getManagedArtifacts,
} from "./EducationSolutionItemDefinition";
import { ArtifactTypeIcon } from "./ArtifactTypeIcon";
import { EducationSolutionItemRibbon } from "./EducationSolutionItemRibbon";
import {
  deployEducationPackage,
  deploymentStateLabel,
  DeploymentItemProgress,
  EDUCATION_PACKAGE_VERSION,
} from "./deploymentService";
import {
  getPollingDelayMs,
  getLatestPipelineJob,
  getPipelineJobStatus,
  getPipelineRunUrl,
  isPipelineJobActive,
  isReportingDataReady,
  listEducationWorkspaceItems,
  pipelineJobStatusLabel,
  resolveBoundItem,
  runPipeline,
  PIPELINE_POLL_TIMEOUT_MS,
} from "./educationService";
import { ensureEducationInstance, migrateLegacyEducationInstance } from "./instanceService";
import {
  getLatestSemanticModelRefresh,
  refreshSemanticModel,
  SemanticModelRefresh,
} from "./reportingService";
import "./EducationSolutionItem.scss";

const TERMINAL_JOB_STATES = new Set(["Completed", "Failed", "Cancelled", "Deduped"]);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "An unexpected Fabric error occurred.";
}

export function EducationSolutionItemEditor(props: PageProps) {
  const { workloadClient } = props;
  const pageContext = useParams<ContextProps>();
  const { pathname } = useLocation();
  const [item, setItem] = useState<ItemWithDefinition<EducationSolutionItemDefinition>>();
  const [definition, setDefinition] = useState<EducationSolutionItemDefinition>(EMPTY_EDUCATION_DEFINITION);
  const [workspaceItems, setWorkspaceItems] = useState<Item[]>([]);
  const [latestJob, setLatestJob] = useState<ItemJobInstance>();
  const [latestSemanticModelRefresh, setLatestSemanticModelRefresh] = useState<SemanticModelRefresh>();
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deploymentComplete, setDeploymentComplete] = useState(false);
  const [deploymentProgress, setDeploymentProgress] = useState<DeploymentItemProgress[]>([]);
  const [includeSampleData, setIncludeSampleData] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [setupStep, setSetupStep] = useState(0);
  const [error, setError] = useState<string>();
  const [viewSetter, setViewSetter] = useState<((view: string) => void) | null>(null);

  const artifactPrefix = definition.instance?.artifactPrefix
    ?? (item ? createArtifactPrefix(item.displayName) : "Education");
  const folderName = definition.instance?.folderName
    ?? (item ? createInstanceFolderName(item.displayName) : "Education");
  const managedArtifacts = getManagedArtifacts(artifactPrefix);
  const managedBindings = managedArtifacts.map((artifact) => ({
    ...artifact,
    item: resolveBoundItem(workspaceItems, definition.artifacts[artifact.key], artifact.type),
  }));
  const missingRequired = managedBindings.filter((binding) => !binding.item);
  const configured = Boolean(definition.schemaVersion === 2
    && definition.instance?.folderId
    && definition.deployment
    && missingRequired.length === 0);
  const report = resolveBoundItem(workspaceItems, definition.artifacts.reportId, "Report");
  const semanticModel = resolveBoundItem(workspaceItems, definition.artifacts.semanticModelId, "SemanticModel");
  const reportingConfigured = Boolean(report && semanticModel);
  const reportingReady = reportingConfigured && isReportingDataReady(latestJob, latestSemanticModelRefresh);
  const pipeline = resolveBoundItem(
    workspaceItems,
    definition.artifacts.processingPipelineId,
    "DataPipeline",
  );
  const isPipelineActive = isRunning || isPipelineJobActive(latestJob?.status);

  useEffect(() => {
    if (!pipeline || isRunning || !isPipelineJobActive(latestJob?.status)) return undefined;

    let cancelled = false;
    let timeoutId: number | undefined;
    const poll = async () => {
      try {
        const status = await getPipelineJobStatus(
          workloadClient,
          definition.workspaceId,
          pipeline.id,
          latestJob.id,
        );
        if (cancelled) return;
        setLatestJob(status.job);
        if (isPipelineJobActive(status.job.status)) {
          timeoutId = window.setTimeout(poll, Math.max(status.retryAfterSeconds, 5) * 1000);
        }
      } catch (pollError) {
        if (cancelled) return;
        setError(errorMessage(pollError));
        timeoutId = window.setTimeout(poll, 5000);
      }
    };

    timeoutId = window.setTimeout(poll, 5000);
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [pipeline?.id, latestJob?.id, isRunning, definition.workspaceId]);

  async function refreshWorkspace(currentItem = item, currentDefinition = definition) {
    if (!currentItem?.workspaceId) return;

    setIsRefreshing(true);
    setError(undefined);
    try {
      const discoveredItems = await listEducationWorkspaceItems(workloadClient, currentItem.workspaceId);
      setWorkspaceItems(discoveredItems);

      if (!currentItem.definition) {
        setDefinition({
          ...EMPTY_EDUCATION_DEFINITION,
          workspaceId: currentItem.workspaceId,
          artifacts: currentDefinition.artifacts,
        });
        setIsDirty(true);
      }

      const pipelineId = currentDefinition.artifacts.processingPipelineId;
      const semanticModelId = currentDefinition.artifacts.semanticModelId;
      const [job, modelRefresh] = await Promise.all([
        pipelineId
          ? getLatestPipelineJob(workloadClient, currentItem.workspaceId, pipelineId)
          : Promise.resolve(undefined),
        semanticModelId
          ? getLatestSemanticModelRefresh(workloadClient, currentItem.workspaceId, semanticModelId)
          : Promise.resolve(undefined),
      ]);
      setLatestJob(job);
      setLatestSemanticModelRefresh(modelRefresh);
    } catch (refreshError) {
      setError(errorMessage(refreshError));
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    async function load() {
      if (!pageContext.itemObjectId) {
        setError(`The Education item ID is missing from ${pathname}.`);
        setIsLoading(false);
        return;
      }

      try {
        const loadedItem = await getWorkloadItem<EducationSolutionItemDefinition>(
          workloadClient,
          pageContext.itemObjectId,
        );
        if (!loadedItem) throw new Error("The Education solution item could not be loaded.");
        if (loadedItem.definition && ![1, 2].includes(loadedItem.definition.schemaVersion)) {
          throw new Error(`Unsupported item definition version: ${loadedItem.definition.schemaVersion}.`);
        }

        const loadedDefinition = loadedItem.definition ?? {
          ...EMPTY_EDUCATION_DEFINITION,
          workspaceId: loadedItem.workspaceId,
        };
        setItem(loadedItem);
        setDefinition(loadedDefinition);
        setIncludeSampleData(!loadedDefinition.deployment);
        await refreshWorkspace(loadedItem, loadedDefinition);
      } catch (loadError) {
        setError(errorMessage(loadError));
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [pageContext.itemObjectId, pathname]);

  useEffect(() => {
    if (!isLoading && viewSetter) {
      viewSetter(configured ? "overview" : "setup");
    }
  }, [configured, isLoading, viewSetter]);

  async function saveItem() {
    if (!item) return;
    setError(undefined);
    const result = await saveWorkloadItem(workloadClient, { ...item, definition });
    if (!result) {
      setError("Fabric did not save the Education solution configuration.");
      return;
    }

    setItem({ ...item, definition });
    setIsDirty(false);
    viewSetter?.("overview");
  }

  async function deployPackage() {
    if (!item?.workspaceId || isDeploying || isPipelineActive) return;
    const isPackageUpdate = Boolean(definition.deployment);
    setIsDeploying(true);
    setError(undefined);
    setDeploymentProgress([]);
    setDeploymentComplete(false);
    try {
      const ownedDefinition = definition.schemaVersion === 1
        ? await migrateLegacyEducationInstance(workloadClient, item.workspaceId, item.displayName, definition)
        : {
            ...definition,
            schemaVersion: 2 as const,
            workspaceId: item.workspaceId,
            instance: await ensureEducationInstance(
              workloadClient,
              item.workspaceId,
              item.displayName,
              definition.instance,
            ),
          };
      const instance = ownedDefinition.instance!;
      const ownershipSave = await saveWorkloadItem(workloadClient, { ...item, definition: ownedDefinition });
      if (!ownershipSave) throw new Error("Fabric did not save the Education solution folder ownership.");
      setDefinition(ownedDefinition);
      setItem({ ...item, definition: ownedDefinition });

      const result = await deployEducationPackage(workloadClient, {
        workspaceId: item.workspaceId,
        instance,
        artifacts: ownedDefinition.artifacts,
        includeSampleData,
      }, (progress) => {
        setDeploymentProgress((current) => {
          const index = current.findIndex((entry) => entry.name === progress.name);
          if (index < 0) return [...current, progress];
          const next = [...current];
          next[index] = progress;
          return next;
        });
      });
      const nextDefinition: EducationSolutionItemDefinition = {
        schemaVersion: 2,
        workspaceId: item.workspaceId,
        artifacts: { ...definition.artifacts, ...result.artifacts },
        instance,
        deployment: {
          packageVersion: EDUCATION_PACKAGE_VERSION,
          completedAtUtc: new Date().toISOString(),
        },
      };
      const saveResult = await saveWorkloadItem(workloadClient, { ...item, definition: nextDefinition });
      if (!saveResult) throw new Error("Artifacts were deployed, but Fabric did not save their ownership metadata.");
      setDefinition(nextDefinition);
      setItem({ ...item, definition: nextDefinition });
      setWorkspaceItems((current) => {
        const byId = new Map(current.map((entry) => [entry.id, entry]));
        result.items.forEach((entry) => byId.set(entry.id, entry));
        return [...byId.values()];
      });
      setIsDirty(false);
      setIncludeSampleData(false);
      setDeploymentComplete(true);
      if (isPackageUpdate && result.artifacts.semanticModelId) {
        try {
          await refreshSemanticModel(workloadClient, item.workspaceId, result.artifacts.semanticModelId);
          setLatestSemanticModelRefresh(await getLatestSemanticModelRefresh(
            workloadClient,
            item.workspaceId,
            result.artifacts.semanticModelId,
          ));
        } catch (refreshError) {
          setError(`Package updated, but semantic model refresh failed. ${errorMessage(refreshError)}`);
        }
      }
    } catch (deploymentError) {
      setError(errorMessage(deploymentError));
    } finally {
      setIsDeploying(false);
    }
  }

  async function openSettings() {
    if (!item) return;
    const result = await callGetItem(workloadClient, item.id);
    if (result?.item) await callOpenSettings(workloadClient, result.item, "About");
  }

  async function openArtifact(boundItem: Item | undefined) {
    if (!boundItem) return;
    try {
      await navigateToItem(workloadClient, boundItem);
    } catch (navigationError) {
      setError(errorMessage(navigationError));
    }
  }

  async function openPipeline(pipelineItem: Item | undefined) {
    if (!pipelineItem) return;
    if (latestJob && isPipelineJobActive(latestJob.status)) {
      try {
        await callNavigationOpenInNewBrowserTab(
          workloadClient,
          getPipelineRunUrl(definition.workspaceId, pipelineItem.id, latestJob.id),
        );
      } catch (navigationError) {
        setError(errorMessage(navigationError));
      }
      return;
    }
    await openArtifact(pipelineItem);
  }

  async function executePipeline() {
    if (!pipeline || isPipelineActive) return;
    setIsRunning(true);
    setError(undefined);
    try {
      const submission = await runPipeline(workloadClient, definition.workspaceId, pipeline.id);
      setLatestJob({
        id: submission.jobId,
        itemId: pipeline.id,
        jobType: "Pipeline",
        invokeType: "Manual",
        status: "NotStarted",
        startTimeUtc: new Date().toISOString(),
      });
      let retryAfterSeconds = submission.retryAfterSeconds;
      const deadline = Date.now() + PIPELINE_POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        const delayMs = getPollingDelayMs(retryAfterSeconds, deadline - Date.now());
        await new Promise((resolve) => window.setTimeout(resolve, delayMs));
        if (Date.now() >= deadline) break;
        const status = await getPipelineJobStatus(workloadClient, definition.workspaceId, pipeline.id, submission.jobId);
        const { job } = status;
        retryAfterSeconds = status.retryAfterSeconds;
        setLatestJob(job);
        if (TERMINAL_JOB_STATES.has(job.status)) {
          if (job.status === "Deduped") {
            throw new Error("End-to-end processing is already running. Open the pipeline to monitor the active job.");
          }
          if (job.status === "Failed" || job.status === "Cancelled") {
            throw new Error(`End-to-end processing ${job.status.toLowerCase()}. Open the pipeline for details.`);
          }
          if (job.status === "Completed" && semanticModel) {
            await refreshSemanticModel(workloadClient, definition.workspaceId, semanticModel.id);
            setLatestSemanticModelRefresh(await getLatestSemanticModelRefresh(
              workloadClient,
              definition.workspaceId,
              semanticModel.id,
            ));
          }
          return;
        }
      }
      throw new Error("End-to-end processing is still running after one hour. Open the pipeline to continue monitoring.");
    } catch (runError) {
      setError(errorMessage(runError));
    } finally {
      setIsRunning(false);
    }
  }

  function SetupView() {
    return (
      <div className="education-shell education-shell--setup">
        <header className="education-heading">
          <div>
            <p className="education-kicker">Education Analytics</p>
            <h1>Set up your Fabric solution</h1>
            <p className="education-summary">Deploy a managed Education package owned by this item.</p>
          </div>
        </header>
        <div className="education-steps" aria-label={`Setup step ${setupStep + 1} of 3`}>
          {["Workspace", "Solution", "Review"].map((label, index) => (
            <div key={label} className={`education-step ${index === setupStep ? "education-step--active" : ""}`}>
              {index + 1}. {label}
            </div>
          ))}
        </div>
        <section className="education-panel education-panel--accent education-panel--setup">
          {setupStep === 0 && (
            <>
              <h2>Current workspace</h2>
              <p>This solution will use the workspace containing the item.</p>
              <div className="education-row">
                <strong>Workspace ID</strong>
                <span className="education-row__meta">{definition.workspaceId || "Unavailable"}</span>
                <span className="education-status"><CheckmarkCircle20Filled /> Selected</span>
              </div>
            </>
          )}
          {setupStep === 1 && (
            <>
              <h2>Solution ownership</h2>
              <p>The item owns one workspace folder. Its name determines every managed artifact name.</p>
              <div className="education-row">
                <strong>Folder</strong>
                <span className="education-row__meta">{folderName}</span>
              </div>
              <div className="education-row">
                <strong>Artifact prefix</strong>
                <span className="education-row__meta">{artifactPrefix}</span>
              </div>
            </>
          )}
          {setupStep === 2 && (
            <>
              <h2>Review and deploy</h2>
              <p>Package {EDUCATION_PACKAGE_VERSION} creates missing artifacts and updates managed notebook and pipeline definitions in this workspace.</p>
              <Checkbox
                checked={includeSampleData}
                disabled={isDeploying}
                label="Upload or refresh Bronze sample data"
                onChange={(_, data) => setIncludeSampleData(data.checked === true)}
              />
              <ul className="education-list">
                {managedArtifacts.map((artifact) => {
                  const boundItem = resolveBoundItem(workspaceItems, definition.artifacts[artifact.key], artifact.type);
                  return (
                    <li className="education-row" key={artifact.key}>
                      <div className="education-artifact">
                        <ArtifactTypeIcon type={artifact.type} />
                        <strong>{artifact.displayName}</strong>
                      </div>
                      <span className="education-row__meta">{artifact.type}</span>
                      <span className="education-status">
                        {boundItem ? <CheckmarkCircle20Filled /> : <Warning20Filled />}
                        {boundItem ? "Deployed" : "Will deploy"}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {deploymentProgress.length > 0 && (
                <section className="education-deployment-progress" aria-live="polite" aria-label="Deployment progress">
                  <h3>Deployment progress</h3>
                  <ul className="education-list">
                    {deploymentProgress.map((progress) => (
                      <li className="education-row" key={progress.name}>
                        <strong>{progress.name}</strong>
                        <span className="education-row__meta">{progress.type}</span>
                        <span className="education-status">{deploymentStateLabel(progress.state)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {deploymentComplete && (
                <div className="education-deployment-success">
                  <MessageBar intent="success"><MessageBarBody>Education package {EDUCATION_PACKAGE_VERSION} is deployed and its ownership metadata is saved.</MessageBarBody></MessageBar>
                </div>
              )}
              <p className="education-note">
                {includeSampleData
                  ? "The manifest and 28 synthetic source CSVs will overwrite the corresponding Bronze landing files."
                  : "Existing Bronze landing files will be left unchanged."}
              </p>
            </>
          )}
          <div className="education-actions education-actions--setup">
            {setupStep > 0 && <Button onClick={() => setSetupStep((step) => step - 1)}>Back</Button>}
            {setupStep < 2 ? (
              <Button appearance="primary" onClick={() => setSetupStep((step) => step + 1)}>Continue</Button>
            ) : (
              <>
                <Button appearance="primary" onClick={deployPackage} disabled={isDeploying || isPipelineActive}>
                  {isDeploying ? "Deploying package" : deploymentComplete ? "Deploy again" : definition.deployment ? "Update package" : "Deploy package"}
                </Button>
                {deploymentComplete && <Button onClick={() => viewSetter?.("overview")}>Open overview</Button>}
              </>
            )}
          </div>
        </section>
      </div>
    );
  }

  function OverviewView() {
    const readyCount = managedBindings.length - missingRequired.length;
    const managedCount = managedBindings.length;
    return (
      <div className="education-shell">
        <header className="education-heading">
          <div>
            <p className="education-kicker">Education Analytics</p>
            <h1>Your data solution, in one place</h1>
            <p className="education-summary">Monitor end-to-end processing and open the managed education report.</p>
          </div>
          <span className="education-status" role="status"><CheckmarkCircle20Filled /> {readyCount}/{managedCount} managed artifacts deployed</span>
        </header>
        <div className="education-grid">
          <section className="education-panel education-panel--accent">
            <h2>Package {definition.deployment?.packageVersion ?? EDUCATION_PACKAGE_VERSION}</h2>
            <div className="education-metric">{readyCount}/{managedCount}</div>
            <p>Three Lakehouses, seven notebooks and one end-to-end processing pipeline.</p>
          </section>
          <section className="education-panel">
            <h2>Latest processing run</h2>
            <div className="education-metric" role="status" aria-live="polite">{pipelineJobStatusLabel(latestJob?.status)}</div>
            <p>{latestJob?.startTimeUtc ? new Date(latestJob.startTimeUtc).toLocaleString() : "No job history is available."}</p>
          </section>
          <section className="education-panel">
            <h2>Reporting</h2>
            <div className="education-metric">{reportingReady ? "Ready" : reportingConfigured ? "Not ready" : "Missing"}</div>
            <p>
              {reportingReady
                ? "The latest completed orchestration run is loaded into the semantic model."
                : reportingConfigured
                  ? "Run the orchestration pipeline and refresh the semantic model to prepare reporting data."
                  : "Update the package to deploy the managed reporting artifacts."}
            </p>
          </section>
          <section className="education-panel education-panel--wide">
            <h2>Medallion flow</h2>
            <div className="education-flow">
              {managedBindings.slice(0, 3).map((binding, index) => (
                <React.Fragment key={binding.key}>
                  {index > 0 && <span className="education-flow__arrow" aria-hidden="true">→</span>}
                  <div className="education-flow__node">
                    <strong>{binding.layer}</strong>
                    <span>{binding.item ? "Deployed" : "Missing"}</span>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </section>
        </div>
      </div>
    );
  }

  function DataView() {
    return (
      <div className="education-shell">
        <header className="education-heading">
          <div>
            <p className="education-kicker">Operations</p>
            <h1>Data flow</h1>
            <p className="education-summary">Inspect deployed artifacts and process source files from Bronze through Gold.</p>
          </div>
          <div className="education-actions">
            <Button onClick={() => { setSetupStep(2); viewSetter?.("setup"); }} disabled={isPipelineActive}>Deploy/update package</Button>
            <Button appearance="primary" icon={<Play20Regular />} onClick={executePipeline} disabled={!pipeline || isPipelineActive}>
              {isPipelineActive ? "Running end-to-end" : "Run end-to-end"}
            </Button>
          </div>
        </header>
        <section className="education-panel education-panel--data">
          <ul className="education-list">
            {managedBindings.map((binding) => (
              <li className="education-row" key={binding.key}>
                <div className="education-artifact">
                  <ArtifactTypeIcon type={binding.type} />
                  <div><strong>{binding.displayName}</strong><div className="education-row__meta">{binding.layer} · {binding.type}</div></div>
                </div>
                <span className="education-status">
                  {binding.type === "DataPipeline" && binding.item
                    ? pipelineJobStatusLabel(latestJob?.status)
                    : binding.item ? "Deployed" : "Missing"}
                </span>
                <Button
                  icon={<Open16Regular />}
                  onClick={() => binding.type === "DataPipeline" ? openPipeline(binding.item) : openArtifact(binding.item)}
                  disabled={!binding.item}
                >
                  {binding.type === "DataPipeline" && isPipelineJobActive(latestJob?.status) ? "Open run" : "Open"}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    );
  }

  function ReportsView() {
    return (
      <div className="education-shell">
        <header className="education-heading">
          <div>
            <p className="education-kicker">Reporting</p>
            <h1>Education insights</h1>
            <p className="education-summary">Open the managed Power BI report over the owned Gold Lakehouse.</p>
          </div>
        </header>
        <section className="education-panel education-panel--wide education-empty">
          {reportingReady ? (
            <>
              <span className="education-status"><CheckmarkCircle20Filled /> Ready</span>
              <h2>{report.displayName}</h2>
              <p>Open the native report to use teacher, school and district experiences with their Fabric security context.</p>
              <Button appearance="primary" icon={<Open16Regular />} onClick={() => openArtifact(report)}>Open report</Button>
            </>
          ) : reportingConfigured ? (
            <>
              <span className="education-status"><Warning20Filled /> Data not ready</span>
              <h2>Complete orchestration before opening the report</h2>
              <p>Run the processing pipeline and wait for its semantic-model refresh to complete.</p>
              <Button appearance="primary" icon={<Play20Regular />} onClick={() => viewSetter?.("data")}>Go to data flow</Button>
            </>
          ) : (
            <>
              <span className="education-status"><Warning20Filled /> Not deployed</span>
              <h2>Power BI is not deployed yet</h2>
              <p>Return to setup and update the package to deploy the semantic model and report.</p>
              <p className="education-note">The package includes class review, student review, school briefing, assignment schedules and district attendance.</p>
              {semanticModel && <Button icon={<Open16Regular />} onClick={() => openArtifact(semanticModel)}>Open semantic model</Button>}
            </>
          )}
        </section>
      </div>
    );
  }

  const views = [
    { name: "setup", component: <SetupView /> },
    { name: "overview", component: <OverviewView /> },
    { name: "data", component: <DataView /> },
    { name: "reports", component: <ReportsView /> },
  ];

  return (
    <ItemEditor
      isLoading={isLoading}
      loadingMessage="Loading Education solution..."
      contentClassName="education-solution"
      initialView="setup"
      viewSetter={(setter) => { if (!viewSetter) setViewSetter(() => setter); }}
      messageBar={error ? [{
        name: "education-error",
        component: <MessageBar intent="error"><MessageBarBody>{error}</MessageBarBody></MessageBar>,
      }] : []}
      ribbon={(context) => (
        <EducationSolutionItemRibbon
          {...props}
          viewContext={context}
          canSave={isDirty}
          isRefreshing={isRefreshing}
          isOperationActive={isDeploying || isPipelineActive}
          onSave={saveItem}
          onRefresh={() => refreshWorkspace()}
          onOpenSettings={openSettings}
        />
      )}
      views={views}
    />
  );
}