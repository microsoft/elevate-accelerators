import React from "react";
import {
  ArrowClockwise24Regular,
  DataTrending24Regular,
  Database24Regular,
  Home24Regular,
} from "@fluentui/react-icons";
import { PageProps } from "../../App";
import {
  Ribbon,
  RibbonAction,
  ViewContext,
  createSaveAction,
  createSettingsAction,
} from "../../components/ItemEditor";
import { isRefreshDisabled } from "./educationService";

interface EducationSolutionItemRibbonProps extends PageProps {
  viewContext: ViewContext;
  canSave: boolean;
  isRefreshing: boolean;
  isOperationActive: boolean;
  onSave: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onOpenSettings: () => Promise<void>;
}

export function EducationSolutionItemRibbon(props: EducationSolutionItemRibbonProps) {
  const navigationActions: RibbonAction[] = [
    {
      key: "overview",
      label: "Overview",
      icon: Home24Regular,
      onClick: () => props.viewContext.setCurrentView("overview"),
    },
    {
      key: "data",
      label: "Data",
      icon: Database24Regular,
      onClick: () => props.viewContext.setCurrentView("data"),
    },
    {
      key: "reports",
      label: "Reports",
      icon: DataTrending24Regular,
      onClick: () => props.viewContext.setCurrentView("reports"),
      showDividerAfter: true,
    },
  ];

  return (
    <Ribbon
      viewContext={props.viewContext}
      homeToolbarActions={[
        ...navigationActions,
        {
          key: "refresh",
          label: props.isRefreshing ? "Refreshing" : "Refresh",
          icon: ArrowClockwise24Regular,
          onClick: props.onRefresh,
          disabled: isRefreshDisabled(props.isRefreshing, props.isOperationActive),
        },
        createSaveAction(props.onSave, !props.canSave),
        createSettingsAction(props.onOpenSettings),
      ]}
    />
  );
}