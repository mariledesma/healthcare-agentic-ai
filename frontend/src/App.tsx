import { useState } from "react";
import "./App.css";


type LLMInfo = {
  provider: string;
  model: string;
};


type Barrier = {
  barrier_id: string;
  finding: string;
  evidence?: string;
  supporting_evidence?: string;
  confidence?: number;
  priority: string;
  source_field: string;
};


type Task = {
  task_id: string;
  task_name: string;
  owner_role: string;
  resolves_barriers: string[];
  priority: string;
  source_field: string;
};


type Recommendation = {
  recommendation_id: string;
  action: string;
  rationale: string;
  owner_role: string;
  priority: string;
  resolves_barriers: string[];
  supporting_task_ids?: string[];
  source_fields?: string[];
};


type GovernanceResult = {
  recommendation_id: string;
  action: string;

  policy: {
    policy_status: string;
    reason?: string;
  };

  approval: {
    approval_status: string;
    requires_human_approval: boolean;
    reason?: string;
  };
};


type EvaluationResult = {
  expected?: string[];
  detected?: string[];
  matched?: string[];
  missed?: string[];
  extra?: string[];
};


type CaseResult = {
  case_id: string;
  condition: string;

  llm_configuration?: {
    case_analyzer?: LLMInfo;
    recommendation_agent?: LLMInfo;
  };

  case_analyzer?: {
    status?: string;
    clinical_summary?: string;
    discharge_summary?: string;
    social_summary?: string;

    potential_concerns?: {
      finding: string;
      supporting_evidence: string;
      source_field: string;
      priority: string;
    }[];

    information_gaps?: string[];

    llm?: LLMInfo;
  };

  barrier_detector?: {
    barriers?: Barrier[];
  };

  task_detector?: {
    tasks?: Task[];
  };

  recommendation_agent?: {
    recommendations?: Recommendation[];
  };

  governance?: {
    status: string;
    recommendations_reviewed: number;
    results?: GovernanceResult[];
  };

  final_output?: {
    final_status?: string;
  };

  evaluation?: {
    barriers?: EvaluationResult;
    tasks?: EvaluationResult;
  };
};


function formatStatus(value?: string) {
  if (!value) {
    return "Unknown";
  }

  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) => letter.toUpperCase()
    );
}


function PriorityBadge({
  priority
}: {
  priority: string;
}) {
  return (
    <span
      className={
        `priority-badge priority-${priority.toLowerCase()}`
      }
    >
      {priority.toUpperCase()}
    </span>
  );
}


function statusClass(
  value?: string,
  requiresHumanApproval?: boolean
) {
  if (requiresHumanApproval) {
    return "status-badge status-danger";
  }

  const status =
    value?.toLowerCase() ?? "";

  if (
    status.includes("blocked") ||
    status.includes("forbidden") ||
    status.includes("required") ||
    status.includes("barrier")
  ) {
    return "status-badge status-danger";
  }

  if (
    status.includes("pending") ||
    status.includes("review") ||
    status.includes("caution")
  ) {
    return "status-badge status-warning";
  }

  if (
    status.includes("allowed") ||
    status.includes("safe") ||
    status.includes("complete") ||
    status.includes("ready") ||
    status.includes("success")
  ) {
    return "status-badge status-success";
  }

  return "status-badge status-neutral";
}


function App() {
  const [caseFile, setCaseFile] =
    useState("case_001_hf.json");

  const [result, setResult] =
    useState<CaseResult | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [activeSection, setActiveSection] =
    useState("overview");


  async function runCase() {
    setLoading(true);
    setError("");
    setResult(null);
    setActiveSection("overview");

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/cases/${caseFile}/run`,
        {
          method: "POST"
        }
      );

      if (!response.ok) {
        throw new Error(
          "The case could not be run."
        );
      }

      const data: CaseResult =
        await response.json();

      setResult(data);

    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(
          "An unexpected error occurred."
        );
      }

    } finally {
      setLoading(false);
    }
  }


  const barriers =
    result?.barrier_detector?.barriers ?? [];

  const tasks =
    result?.task_detector?.tasks ?? [];

  const recommendations =
    result?.recommendation_agent
      ?.recommendations ?? [];

  const governance =
    result?.governance?.results ?? [];


  function renderOverview() {
    if (!result) {
      return null;
    }

    return (
      <>
        <section className="clinical-panel">

          <div className="panel-header">
            <h2>Patient Overview</h2>

            <span className="panel-subtitle">
              LLM Case Analysis
            </span>
          </div>

          <div className="clinical-summary-grid">

            <div className="summary-column">
              <h3>Clinical</h3>

              <p>
                {result.case_analyzer
                  ?.clinical_summary ??
                  "No clinical summary available."}
              </p>
            </div>

            <div className="summary-column">
              <h3>Discharge</h3>

              <p>
                {result.case_analyzer
                  ?.discharge_summary ??
                  "No discharge summary available."}
              </p>
            </div>

            <div className="summary-column">
              <h3>Social / Logistical</h3>

              <p>
                {result.case_analyzer
                  ?.social_summary ??
                  "No social summary available."}
              </p>
            </div>

          </div>

        </section>


        <section className="clinical-panel">

          <div className="panel-header">

            <h2>
              Active Discharge Barriers
            </h2>

            <span className="count-badge">
              {barriers.length}
            </span>

          </div>

          {barriers.length === 0 ? (
            <div className="empty-state success-outline">
              No active discharge barriers detected.
            </div>
          ) : (
            <div className="clinical-table">

              <div className="table-header">
                <span>ID</span>
                <span>Barrier</span>
                <span>Priority</span>
                <span>Evidence</span>
              </div>

              {barriers.map(
                (barrier) => (
                  <div
                    className="table-row"
                    key={
                      barrier.barrier_id
                    }
                  >

                    <span className="clinical-id">
                      {barrier.barrier_id}
                    </span>

                    <span>
                      {barrier.finding}
                    </span>

                    <span>
                      <PriorityBadge
                        priority={
                          barrier.priority
                        }
                      />
                    </span>

                    <span className="table-evidence">
                      {barrier.evidence ??
                        barrier
                          .supporting_evidence ??
                        barrier.source_field}
                    </span>

                  </div>
                )
              )}

            </div>
          )}

        </section>


        <div className="workspace-columns">

          <section className="clinical-panel">

            <div className="panel-header">
              <h2>Pending Tasks</h2>

              <span className="count-badge">
                {tasks.length}
              </span>
            </div>

            {tasks.length === 0 && (
              <div className="empty-state success-outline">
                No pending tasks.
              </div>
            )}

            {tasks.map((task) => (
              <div
                className="compact-item"
                key={task.task_id}
              >

                <div>
                  <span className="clinical-id">
                    {task.task_id}
                  </span>

                  <strong>
                    {task.task_name}
                  </strong>
                </div>

                <div className="compact-right">
                  <PriorityBadge
                    priority={
                      task.priority
                    }
                  />

                  <span className="compact-meta">
                    {task.owner_role}
                  </span>
                </div>

              </div>
            ))}

          </section>


          <section className="clinical-panel">

            <div className="panel-header">
              <h2>Recommendations</h2>

              <span className="count-badge">
                {recommendations.length}
              </span>
            </div>

            {recommendations.map(
              (recommendation) => (
                <div
                  className="recommendation-item"
                  key={
                    recommendation
                      .recommendation_id
                  }
                >

                  <div className="recommendation-title">

                    <span className="clinical-id">
                      {
                        recommendation
                          .recommendation_id
                      }
                    </span>

                    <strong>
                      {
                        recommendation
                          .action
                      }
                    </strong>

                    <PriorityBadge
                      priority={
                        recommendation
                          .priority
                      }
                    />

                  </div>

                  <p>
                    {
                      recommendation
                        .rationale
                    }
                  </p>

                  <span className="compact-meta">
                    Owner:{" "}
                    {
                      recommendation
                        .owner_role
                    }
                  </span>

                </div>
              )
            )}

          </section>

        </div>


        <section className="clinical-panel">

          <div className="panel-header">

            <h2>
              Governance Summary
            </h2>

          </div>

          {governance.map((item) => (
            <div
              className="governance-summary-row"
              key={
                item.recommendation_id
              }
            >

              <strong>
                {item.action}
              </strong>

              <span
                className={statusClass(
                  item.policy
                    .policy_status
                )}
              >
                Policy:{" "}
                {formatStatus(
                  item.policy
                    .policy_status
                )}
              </span>

              <span
                className={statusClass(
                  item.approval
                    .approval_status,
                  item.approval
                    .requires_human_approval
                )}
              >
                {item.approval
                  .requires_human_approval
                  ? "Human Review Required"
                  : "No Human Review Required"}
              </span>

            </div>
          ))}

        </section>
      </>
    );
  }


  function renderBarriers() {
    return (
      <section className="clinical-panel">

        <div className="panel-header">
          <h2>Barrier Review</h2>

          <span className="count-badge">
            {barriers.length}
          </span>
        </div>

        {barriers.length === 0 ? (
          <div className="empty-state success-outline">
            No discharge barriers detected.
          </div>
        ) : (
          <div className="clinical-table">

            <div className="table-header barrier-detail-grid">
              <span>ID</span>
              <span>Finding</span>
              <span>Priority</span>
              <span>Source</span>
              <span>Evidence</span>
            </div>

            {barriers.map(
              (barrier) => (
                <div
                  className="table-row barrier-detail-grid"
                  key={
                    barrier.barrier_id
                  }
                >

                  <span className="clinical-id">
                    {barrier.barrier_id}
                  </span>

                  <span>
                    {barrier.finding}
                  </span>

                  <span>
                    <PriorityBadge
                      priority={
                        barrier.priority
                      }
                    />
                  </span>

                  <span className="compact-meta">
                    {barrier.source_field}
                  </span>

                  <span>
                    {barrier.evidence ??
                      barrier
                        .supporting_evidence}
                  </span>

                </div>
              )
            )}

          </div>
        )}

      </section>
    );
  }


  function renderTasks() {
    return (
      <section className="clinical-panel">

        <div className="panel-header">
          <h2>Task Management</h2>

          <span className="count-badge">
            {tasks.length}
          </span>
        </div>

        <div className="clinical-table">

          <div className="table-header task-grid">
            <span>ID</span>
            <span>Task</span>
            <span>Owner</span>
            <span>Priority</span>
            <span>Barrier</span>
          </div>

          {tasks.map((task) => (
            <div
              className="table-row task-grid"
              key={task.task_id}
            >

              <span className="clinical-id">
                {task.task_id}
              </span>

              <span>
                {task.task_name}
              </span>

              <span>
                {task.owner_role}
              </span>

              <span>
                <PriorityBadge
                  priority={
                    task.priority
                  }
                />
              </span>

              <span>
                {task.resolves_barriers
                  ?.join(", ")}
              </span>

            </div>
          ))}

        </div>

      </section>
    );
  }


  function renderRecommendations() {
    return (
      <section className="clinical-panel">

        <div className="panel-header">

          <h2>
            AI Recommendations
          </h2>

          <span className="panel-subtitle">
            Decision Support Only
          </span>

        </div>

        {recommendations.map(
          (recommendation) => (
            <div
              className="recommendation-detail"
              key={
                recommendation
                  .recommendation_id
              }
            >

              <div className="recommendation-title">

                <span className="clinical-id">
                  {
                    recommendation
                      .recommendation_id
                  }
                </span>

                <strong>
                  {recommendation.action}
                </strong>

                <PriorityBadge
                  priority={
                    recommendation.priority
                  }
                />

              </div>

              <p>
                {recommendation.rationale}
              </p>

              <div className="detail-footer">

                <span>
                  Owner:{" "}
                  {
                    recommendation
                      .owner_role
                  }
                </span>

                <span>
                  Related barriers:{" "}
                  {recommendation
                    .resolves_barriers
                    ?.join(", ")}
                </span>

              </div>

            </div>
          )
        )}

      </section>
    );
  }


  function renderGovernance() {
    return (
      <section className="clinical-panel">

        <div className="panel-header">
          <h2>
            Governance & Approval
          </h2>
        </div>

        <div className="clinical-table">

          <div className="table-header governance-grid">
            <span>Action</span>
            <span>Policy</span>
            <span>Approval</span>
            <span>Human Review</span>
          </div>

          {governance.map((item) => (
            <div
              className="table-row governance-grid"
              key={
                item.recommendation_id
              }
            >

              <span>
                {item.action}
              </span>

              <span
                className={statusClass(
                  item.policy
                    .policy_status
                )}
              >
                {formatStatus(
                  item.policy
                    .policy_status
                )}
              </span>

              <span
                className={statusClass(
                  item.approval
                    .approval_status
                )}
              >
                {formatStatus(
                  item.approval
                    .approval_status
                )}
              </span>

              <span
                className={statusClass(
                  item.approval
                    .requires_human_approval
                    ? "required"
                    : "safe",
                  item.approval
                    .requires_human_approval
                )}
              >
                {item.approval
                  .requires_human_approval
                  ? "Required"
                  : "Not Required"}
              </span>

            </div>
          ))}

        </div>

      </section>
    );
  }


  function renderEvaluation() {
    return (
      <section className="clinical-panel">

        <div className="panel-header">
          <h2>
            Research Evaluation
          </h2>
        </div>

        <div className="evaluation-columns">

          <div>
            <h3>Barriers</h3>

            <div className="evaluation-row">
              <span>Expected</span>

              <strong>
                {result?.evaluation
                  ?.barriers
                  ?.expected
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Detected</span>

              <strong>
                {result?.evaluation
                  ?.barriers
                  ?.detected
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Missed</span>

              <strong
                className={
                  result?.evaluation
                    ?.barriers
                    ?.missed?.length
                    ? "evaluation-alert"
                    : "evaluation-success"
                }
              >
                {result?.evaluation
                  ?.barriers
                  ?.missed
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Extra</span>

              <strong
                className={
                  result?.evaluation
                    ?.barriers
                    ?.extra?.length
                    ? "evaluation-warning"
                    : "evaluation-success"
                }
              >
                {result?.evaluation
                  ?.barriers
                  ?.extra
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>
          </div>


          <div>
            <h3>Tasks</h3>

            <div className="evaluation-row">
              <span>Expected</span>

              <strong>
                {result?.evaluation
                  ?.tasks
                  ?.expected
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Detected</span>

              <strong>
                {result?.evaluation
                  ?.tasks
                  ?.detected
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Missed</span>

              <strong
                className={
                  result?.evaluation
                    ?.tasks
                    ?.missed?.length
                    ? "evaluation-alert"
                    : "evaluation-success"
                }
              >
                {result?.evaluation
                  ?.tasks
                  ?.missed
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

            <div className="evaluation-row">
              <span>Extra</span>

              <strong
                className={
                  result?.evaluation
                    ?.tasks
                    ?.extra?.length
                    ? "evaluation-warning"
                    : "evaluation-success"
                }
              >
                {result?.evaluation
                  ?.tasks
                  ?.extra
                  ?.join(", ") ||
                  "None"}
              </strong>
            </div>

          </div>

        </div>

      </section>
    );
  }


  function renderWorkspace() {
    if (!result) {
      return (
        <div className="welcome-state">

          <h2>
            Discharge Coordination
          </h2>

          <p>
            Select a synthetic patient case
            and run the analysis to begin.
          </p>

        </div>
      );
    }

    if (activeSection === "barriers") {
      return renderBarriers();
    }

    if (activeSection === "tasks") {
      return renderTasks();
    }

    if (
      activeSection ===
      "recommendations"
    ) {
      return renderRecommendations();
    }

    if (
      activeSection === "governance"
    ) {
      return renderGovernance();
    }

    if (
      activeSection === "evaluation"
    ) {
      return renderEvaluation();
    }

    return renderOverview();
  }


  return (
    <div className="ehr-app">

      <header className="application-header">

        <div className="brand">

          <div className="brand-mark">
            HAI
          </div>

          <div>
            <strong>
              Healthcare Agentic AI
            </strong>

            <span>
              Discharge Coordination
            </span>
          </div>

        </div>

        <div className="research-label">
          RESEARCH PROTOTYPE
        </div>

      </header>


      <div className="case-toolbar">

        <div className="case-selector">

          <label>
            Patient Case
          </label>

          <select
            value={caseFile}
            onChange={(event) =>
              setCaseFile(
                event.target.value
              )
            }
          >
            <option value="case_001_hf.json">
              CASE-001 — Heart Failure
            </option>

            <option value="case_002_copd.json">
              CASE-002 — COPD
            </option>

            <option value="case_003_pneumonia.json">
              CASE-003 — Pneumonia
            </option>

            <option value="case_004_ortho.json">
              CASE-004 — Orthopedic
            </option>

            <option value="case_005_stroke.json">
              CASE-005 — Stroke
            </option>

            <option value="case_006_transport_timing.json">
              CASE-006 — Transport Timing Conflict
            </option>
          </select>

          <button
            onClick={runCase}
            disabled={loading}
          >
            {loading
              ? "Analyzing..."
              : "Run Analysis"}
          </button>

        </div>


        {result && (
          <div className="patient-banner">

            <div>
              <span className="banner-label">
                Case
              </span>

              <strong>
                {result.case_id}
              </strong>
            </div>

            <div>
              <span className="banner-label">
                Condition
              </span>

              <strong>
                {result.condition}
              </strong>
            </div>

            <div>
              <span className="banner-label">
                Barriers
              </span>

              <strong>
                {barriers.length}
              </strong>
            </div>

            <div>
              <span className="banner-label">
                Tasks
              </span>

              <strong>
                {tasks.length}
              </strong>
            </div>

            <div>
              <span className="banner-label">
                Discharge Status
              </span>

              <span
                className={statusClass(
                  result.final_output
                    ?.final_status
                )}
              >
                {formatStatus(
                  result.final_output
                    ?.final_status
                )}
              </span>
            </div>

          </div>
        )}

      </div>


      {error && (
        <div className="global-error">
          {error}
        </div>
      )}


      <div className="main-layout">

        <aside className="sidebar">

          <button
            className={
              activeSection === "overview"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "overview"
              )
            }
          >
            Overview
          </button>


          <button
            className={
              activeSection === "barriers"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "barriers"
              )
            }
          >
            Barriers

            {result && (
              <span className="nav-count">
                {barriers.length}
              </span>
            )}
          </button>


          <button
            className={
              activeSection === "tasks"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "tasks"
              )
            }
          >
            Tasks

            {result && (
              <span className="nav-count">
                {tasks.length}
              </span>
            )}
          </button>


          <button
            className={
              activeSection ===
              "recommendations"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "recommendations"
              )
            }
          >
            Recommendations
          </button>


          <button
            className={
              activeSection ===
              "governance"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "governance"
              )
            }
          >
            Governance
          </button>


          <button
            className={
              activeSection ===
              "evaluation"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() =>
              setActiveSection(
                "evaluation"
              )
            }
          >
            Evaluation
          </button>


          {result && (
            <div className="sidebar-model">

              <span>
                LLM Provider
              </span>

              <strong>
                {result
                  .llm_configuration
                  ?.case_analyzer
                  ?.provider ??
                  "Unknown"}
              </strong>

              <span>
                Model
              </span>

              <strong>
                {result
                  .llm_configuration
                  ?.case_analyzer
                  ?.model ??
                  "Unknown"}
              </strong>

            </div>
          )}

        </aside>


        <section className="workspace">
          {renderWorkspace()}
        </section>

      </div>

    </div>
  );
}


export default App;