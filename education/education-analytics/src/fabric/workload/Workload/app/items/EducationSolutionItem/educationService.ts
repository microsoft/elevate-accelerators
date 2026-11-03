import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { Item, ItemJobInstance } from "../../clients/FabricPlatformTypes";
import { ItemClient } from "../../clients/ItemClient";
import { JobSchedulerClient } from "../../clients/JobSchedulerClient";
import type { SemanticModelRefresh } from "./reportingService";

export async function listEducationWorkspaceItems(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
): Promise<Item[]> {
  return new ItemClient(workloadClient).getAllItems(workspaceId);
}

export function resolveBoundItem(
  items: Item[],
  bindingId: string | undefined,
  expectedType: string,
): Item | undefined {
  return items.find((item) => item.id === bindingId && item.type === expectedType);
}

export async function getLatestPipelineJob(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  pipelineId: string,
): Promise<ItemJobInstance | undefined> {
  const jobs = await new JobSchedulerClient(workloadClient).getAllItemJobInstances(
    workspaceId,
    pipelineId,
  );
  return jobs.sort((left, right) => (right.startTimeUtc ?? "").localeCompare(left.startTimeUtc ?? ""))[0];
}

export async function runPipeline(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  pipelineId: string,
): Promise<{ jobId: string; retryAfterSeconds: number }> {
  return new JobSchedulerClient(workloadClient).runOnDemandItemJob(
    workspaceId,
    pipelineId,
    "Pipeline",
  );
}

export async function getPipelineJobStatus(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  pipelineId: string,
  jobId: string,
): Promise<{ job: ItemJobInstance; retryAfterSeconds: number }> {
  return new JobSchedulerClient(workloadClient).getItemJobInstanceStatus(workspaceId, pipelineId, jobId);
}

export const PIPELINE_POLL_TIMEOUT_MS = 60 * 60 * 1000;

export function getPipelineRunPath(workspaceId: string, pipelineId: string, jobId: string): string {
  return `/workloads/data-pipeline/monitoring/workspaces/${encodeURIComponent(workspaceId)}`
    + `/pipelines/${encodeURIComponent(pipelineId)}/${encodeURIComponent(jobId)}`;
}

export function getPipelineRunUrl(workspaceId: string, pipelineId: string, jobId: string): string {
  return `https://app.fabric.microsoft.com${getPipelineRunPath(workspaceId, pipelineId, jobId)}`;
}

export function getPollingDelayMs(retryAfterSeconds: number, remainingMs: number): number {
  return Math.max(0, Math.min(retryAfterSeconds * 1000, remainingMs));
}

export function isRefreshDisabled(isRefreshing: boolean, isOperationActive: boolean): boolean {
  return isRefreshing || isOperationActive;
}

export function isPipelineJobActive(status: ItemJobInstance["status"] | undefined): boolean {
  return status === "NotStarted" || status === "InProgress";
}

function parseFabricUtcTimestamp(value: string): number {
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  return Date.parse(hasTimezone ? value : `${value}Z`);
}

export function isReportingDataReady(
  latestJob: ItemJobInstance | undefined,
  latestRefresh: SemanticModelRefresh | undefined,
): boolean {
  if (latestJob?.status !== "Completed" || latestRefresh?.status !== "Completed") return false;
  if (!latestJob.endTimeUtc || !latestRefresh.endTime) return false;

  const pipelineCompletedAt = parseFabricUtcTimestamp(latestJob.endTimeUtc);
  const modelRefreshedAt = parseFabricUtcTimestamp(latestRefresh.endTime);
  return Number.isFinite(pipelineCompletedAt)
    && Number.isFinite(modelRefreshedAt)
    && modelRefreshedAt >= pipelineCompletedAt;
}

export function pipelineJobStatusLabel(status: ItemJobInstance["status"] | undefined): string {
  if (!status) return "Not run";
  if (status === "NotStarted") return "Queued";
  if (status === "InProgress") return "Running";
  return status;
}