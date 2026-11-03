import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, FluentProvider } from "@fluentui/react-components";
import { Database20Regular, Home20Regular, Open16Regular, Play20Regular, DataTrending20Regular } from "@fluentui/react-icons";
import { fabricLightTheme } from "./theme";
import { ArtifactTypeIcon } from "./items/EducationSolutionItem/ArtifactTypeIcon";
import "./items/EducationSolutionItem/EducationSolutionItem.scss";

type PreviewView = "overview" | "data" | "reports";

const artifacts = [
    ["EDU_Bronze", "Bronze", "Lakehouse"],
    ["EDU_SL", "Silver", "Lakehouse"],
    ["EDU_GD", "Gold", "Lakehouse"],
    ["EDU_BR_GD_Processing", "Flow", "Data pipeline"],
];

function Preview() {
    const [view, setView] = useState<PreviewView>("overview");
    return (
        <FluentProvider theme={fabricLightTheme}>
            <div className="education-preview-ribbon" role="navigation" aria-label="Preview navigation">
                <Button appearance={view === "overview" ? "primary" : "subtle"} icon={<Home20Regular />} onClick={() => setView("overview")}>Overview</Button>
                <Button appearance={view === "data" ? "primary" : "subtle"} icon={<Database20Regular />} onClick={() => setView("data")}>Data</Button>
                <Button appearance={view === "reports" ? "primary" : "subtle"} icon={<DataTrending20Regular />} onClick={() => setView("reports")}>Reports</Button>
            </div>
            <main className="education-solution">
                {view === "overview" && <div className="education-shell">
                    <header className="education-heading">
                        <div><p className="education-kicker">Education Analytics</p><h1>Your data solution, in one place</h1><p className="education-summary">Monitor the medallion flow, refresh Gold, and attach reporting when it is ready.</p></div>
                        <span className="education-status">4/4 core artifacts deployed</span>
                    </header>
                    <div className="education-grid">
                        <section className="education-panel education-panel--accent"><h2>Core artifacts</h2><div className="education-metric">4/4</div><p>Bronze, Silver, Gold and end-to-end processing pipeline.</p></section>
                        <section className="education-panel"><h2>Latest processing run</h2><div className="education-metric" role="status" aria-live="polite">Completed</div><p>Today at 09:42</p></section>
                        <section className="education-panel"><h2>Reporting</h2><div className="education-metric">Next</div><p>Power BI can be configured here when available.</p></section>
                        <section className="education-panel education-panel--wide"><h2>Medallion flow</h2><div className="education-flow"><div className="education-flow__node"><strong>Bronze</strong><span>Deployed</span></div><span className="education-flow__arrow">→</span><div className="education-flow__node"><strong>Silver</strong><span>Deployed</span></div><span className="education-flow__arrow">→</span><div className="education-flow__node"><strong>Gold</strong><span>Deployed</span></div></div></section>
                    </div>
                </div>}
                {view === "data" && <div className="education-shell"><header className="education-heading"><div><p className="education-kicker">Operations</p><h1>Data flow</h1><p className="education-summary">Deploy managed artifacts and process source files from Bronze through Gold.</p></div><div className="education-actions"><Button>Deploy/update package</Button><Button appearance="primary" icon={<Play20Regular />}>Run end-to-end</Button></div></header><section className="education-panel"><ul className="education-list">{artifacts.map(([name, layer, type]) => <li className="education-row" key={name}><div className="education-artifact"><ArtifactTypeIcon type={type} /><div><strong>{name}</strong><div className="education-row__meta">{layer} · {type}</div></div></div><span className="education-status">{type === "Data pipeline" ? "Not run" : "Deployed"}</span><Button icon={<Open16Regular />}>Open</Button></li>)}</ul></section></div>}
                {view === "reports" && <div className="education-shell"><header className="education-heading"><div><p className="education-kicker">Reporting</p><h1>Education insights</h1><p className="education-summary">The solution is ready for governed Power BI reporting when those artifacts are delivered.</p></div></header><section className="education-panel education-panel--wide education-empty"><span className="education-status">Coming later</span><h2>Power BI is not configured yet</h2><p>The medallion solution works independently. Attach reporting when the semantic model and report are ready.</p><p className="education-note">Planned experiences: class review, student review, school briefing, assignment schedules and district attendance.</p></section></div>}
            </main>
        </FluentProvider>
    );
}

export function initializeStandalonePreview() {
    const root = document.getElementById("root");
    if (!root) throw new Error("Preview root element is missing.");
    createRoot(root).render(<Preview />);
}