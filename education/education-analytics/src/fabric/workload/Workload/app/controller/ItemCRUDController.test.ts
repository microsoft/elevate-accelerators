import assert from "node:assert/strict";
import { describe, it } from "node:test";

describe("getWorkloadItem", () => {
  it("rejects when Fabric item metadata cannot be loaded", async () => {
    const originalConsoleError = console.error;
    console.error = () => undefined;
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: { parent: {} },
    });
    const { getWorkloadItem } = await import("./ItemCRUDController");
    const workloadClient = {
      itemCrud: {
        getItem: async () => { throw new Error("not found"); },
        getItemDefinition: async () => ({ definition: { parts: [] as unknown[] } }),
      },
    } as never;

    try {
      await assert.rejects(
        () => getWorkloadItem(workloadClient, "missing-item"),
        /Item missing-item could not be loaded/,
      );
    } finally {
      console.error = originalConsoleError;
    }
  });
});
