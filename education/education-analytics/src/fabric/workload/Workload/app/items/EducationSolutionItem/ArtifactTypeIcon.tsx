import React from "react";

const ICON_NAMES: Record<string, string> = {
  datapipeline: "pipeline",
  lakehouse: "lakehouse",
  notebook: "notebook",
  report: "report",
  semanticmodel: "semantic_model",
};

export function getArtifactTypeIconPath(type: string): string | undefined {
  const iconName = ICON_NAMES[type.toLowerCase().replace(/[\s_-]/g, "")];
  return iconName ? `/assets/icons/${iconName}_32_item.svg` : undefined;
}

export function ArtifactTypeIcon({ type }: { type: string }) {
  const source = getArtifactTypeIconPath(type);
  if (!source) return null;

  return <img className="education-artifact__icon" src={source} alt="" aria-hidden="true" />;
}
