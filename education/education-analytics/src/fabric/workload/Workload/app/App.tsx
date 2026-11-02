import React from "react";
import { Route, Router, Switch } from "react-router-dom";
import { History } from "history";
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { EducationSolutionItemEditor } from "./items/EducationSolutionItem";

/*
    Add your Item Editor in the Route section of the App function below
*/

interface AppProps {
    history: History;
    workloadClient: WorkloadClientAPI;
}

export interface PageProps {
    workloadClient: WorkloadClientAPI;
    history?: History
}

export interface ContextProps {
    itemObjectId?: string;
    workspaceObjectId?: string
    source?: string;
}

export interface SharedState {
    message: string;
}

export function App({ history, workloadClient }: AppProps) {
    return <Router history={history}>
        <Switch>
            <Route path="/EducationSolutionItem-editor/:itemObjectId">
                <EducationSolutionItemEditor workloadClient={workloadClient} />
            </Route>
            <Route path="/">
                <main className="education-solution">
                    <div className="education-shell">
                        <section className="education-panel education-panel--accent education-empty">
                            <p className="education-kicker">Education Analytics</p>
                            <h1>Open an Education Solution item</h1>
                            <p>The workload is running. Create or open an Education Solution item from your Fabric workspace.</p>
                        </section>
                    </div>
                </main>
            </Route>
        </Switch>
    </Router>;
}