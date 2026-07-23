import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  FileText,
  UploadCloud,
  RefreshCw,
  CheckCircle2,
  Circle,
  ThumbsUp,
  AlertTriangle,
  Sparkles,
  Star,
  Clock,
  Gauge,
  Grid3x3,
  Download,
  Trash2,
  Eye,
  Loader2,
} from "lucide-react";

/* =========================================================================
   MOCK MODE
exact same request/response shapes documented in
   INSTRUCTIONS.md (POST /grade, GET /result/{job_id}) using setTimeout.

   To go live later: delete the two mock functions and the "MOCK CALLS"
   block inside startGrading/pollResult, and uncomment the real fetch()
   calls right below them (left in as comments for a fast swap).
   ========================================================================= */
const API_BASE = "http://localhost:8000"; // change to your backend URL when ready
const POLL_INTERVAL_MS = 1500; // faster than real 3-5s so demos don't drag
const MOCK_PROCESSING_TICKS = 4; // how many "processing" polls before resolving

// A dummy version of what GET /result/{job_id} returns once status:"graded"
// Shape copied 1:1 from the "Response when graded" example in INSTRUCTIONS.md
function buildDummyGradedResponse(jobId, fileName) {
  return {
    job_id: jobId,
    status: "graded",
    total_score: 17,
    max_score: 22,
    percentage: 77.3,
    grade: "B",
    reliability_score: 87,
    reliability_level: "high",
    reliability_message: "Word-level remarks on this submission are accurate",
    graded_pdf_url: "#dummy-graded-pdf", // no real file in mock mode
    graded_at: new Date().toISOString(),
    source_file: fileName,
    breakdown: [
      {
        question: "Q1",
        type: "mcq",
        score: 2,
        max_score: 2,
        feedback: "Correct",
      },
      {
        question: "Q2",
        type: "written",
        score: 8,
        max_score: 10,
        feedback:
          "Good explanation of evaporation and condensation. Did not mention precipitation.",
        spelling_mistakes: ["evapration"],
        annotation_level: "word",
        confidence: 0.92,
      },
      {
        question: "Q3",
        type: "written",
        score: 7,
        max_score: 10,
        feedback: "Mentioned sunlight correctly but missed chlorophyll entirely.",
        spelling_mistakes: ["photosinthesis"],
        annotation_level: "word",
        confidence: 0.88,
      },
    ],
  };
}

// Occasionally return the "review_needed" shape instead, so you can test
// that path too — flip FORCE_REVIEW_NEEDED to true to always see it.
const FORCE_REVIEW_NEEDED = false;
function buildDummyReviewResponse(jobId) {
  return {
    job_id: jobId,
    status: "review_needed",
    reason:
      "Low handwriting reliability (54%). Word-level remarks may be inaccurate. Teacher review required.",
  };
}

/** Fakes POST /grade — resolves with { job_id, status: "processing", submitted_at } */
function mockGradeRequest(file) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        job_id: `mock-${Date.now()}`,
        status: "processing",
        submitted_at: new Date().toISOString(),
      });
    }, 900); // simulate upload/network latency
  });
}

/** Fakes one GET /result/{job_id} poll. Returns "processing" for the first
 *  MOCK_PROCESSING_TICKS calls, then resolves to graded/review_needed. */
function mockPollResult(jobId, tickCount, fileName) {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (tickCount < MOCK_PROCESSING_TICKS) {
        resolve({ job_id: jobId, status: "processing" });
      } else if (FORCE_REVIEW_NEEDED) {
        resolve(buildDummyReviewResponse(jobId));
      } else {
        resolve(buildDummyGradedResponse(jobId, fileName));
      }
    }, 400);
  });
}

/* 
   Answer key that WOULD be sent to POST /grade alongside the PDF in real
   mode. Kept here only so the mock call signature matches the real one.
    */
const SAMPLE_ANSWER_KEY = {
  Q1: { type: "mcq", answer: "B", marks: 2 },
  Q2: {
    type: "written",
    answer: "The water cycle involves evaporation, condensation, and precipitation.",
    rubric: "Award 3 marks for evaporation, 3 for condensation, 4 for precipitation",
    marks: 10,
  },
  Q3: {
    type: "written",
    answer: "Photosynthesis is the process by which plants convert sunlight into food.",
    rubric: "Award 5 marks for mentioning sunlight, 5 for mentioning chlorophyll",
    marks: 10,
  },
};

/* 
   Small presentational helpers
   */

const Card = ({ children, className = "" }) => (
  <div
    className={`bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_2px_rgba(15,23,42,0.04)] p-5 ${className}`}
  >
    {children}
  </div>
);

const CardHeader = ({ icon: Icon, iconClass, title, titleClass = "" }) => (
  <div className="flex items-center gap-2 mb-4">
    <Icon size={18} className={iconClass} />
    <h3 className={`font-semibold text-[15px] ${titleClass}`}>{title}</h3>
  </div>
);

const pillColor = (level) => {
  switch (level) {
    case "high":
      return "bg-green-50 text-green-600";
    case "medium":
      return "bg-amber-50 text-amber-600";
    case "low":
      return "bg-red-50 text-red-600";
    default:
      return "bg-slate-50 text-slate-600";
  }
};

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

const ScoreRing = ({ percentage = 0 }) => {
  const radius = 72;
  const stroke = 12;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, percentage)) / 100;
  const offset = circumference * (1 - pct);
  const ringColor = percentage >= 75 ? "#22C55E" : percentage >= 50 ? "#F59E0B" : "#EF4444";

  return (
    <div className="relative w-[180px] h-[180px] mx-auto">
      <svg width="180" height="180" viewBox="0 0 180 180" className="-rotate-90">
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#EEF2F7" strokeWidth={stroke} />
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke={ringColor}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl font-bold text-slate-800 leading-none">
          {Math.round(percentage)}
        </span>
        <span className="text-slate-400 text-sm mt-1">%</span>
      </div>
    </div>
  );
};

const PROGRESS_STEPS = [
  "Uploading File",
  "Validating PDF",
  "Reading & Grading",
  "Checking Reliability",
  "Generating Feedback",
  "Completed",
];

function ProgressStepper({ stage, done }) {
  return (
    <Card>
      <CardHeader icon={Sparkles} iconClass="text-blue-500" title="AI Evaluation Progress" />
      <div className="flex flex-col gap-3">
        {PROGRESS_STEPS.map((step, i) => {
          const isDone = done || i < stage;
          const isCurrent = !done && i === stage;
          return (
            <div key={step} className="flex items-center gap-3">
              {isDone ? (
                <CheckCircle2 size={16} className="text-green-500 shrink-0" />
              ) : isCurrent ? (
                <Loader2 size={16} className="text-blue-500 shrink-0 animate-spin" />
              ) : (
                <Circle size={16} className="text-slate-300 shrink-0" />
              )}
              <span
                className={`text-sm flex-1 ${
                  isCurrent ? "text-blue-600 font-semibold" : isDone ? "text-slate-600" : "text-slate-400"
                }`}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-4">
        <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${done ? 100 : (stage / (PROGRESS_STEPS.length - 1)) * 100}%` }}
          />
        </div>
        <div className="text-right text-xs font-semibold text-blue-600 mt-1">
          {done ? 100 : Math.round((stage / (PROGRESS_STEPS.length - 1)) * 100)}%
        </div>
      </div>
    </Card>
  );
}

 //  Main component

export default function GradingDashboardMock() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | processing | graded | review_needed | failed
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [progressStage, setProgressStage] = useState(0);

  const pollTimeoutRef = useRef(null);
  const stageIntervalRef = useRef(null);
  const tickCountRef = useRef(0);
  const fileInputRef = useRef(null);

  const isBusy = status === "processing";
  const isDone = status === "graded" || status === "review_needed";

  const resetAll = () => {
    clearTimeout(pollTimeoutRef.current);
    clearInterval(stageIntervalRef.current);
    tickCountRef.current = 0;
    setFile(null);
    setJobId(null);
    setStatus("idle");
    setResult(null);
    setErrorMsg(null);
    setProgressStage(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.type !== "application/pdf") {
      setErrorMsg("Only PDF files are supported.");
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setErrorMsg("File exceeds the 20MB limit.");
      return;
    }
    setErrorMsg(null);
    setFile(f);
  };

  /* ---- "POST /grade" (mocked) ---------------------------------------- */
  const startGrading = async () => {
    if (!file) return;
    setErrorMsg(null);
    setStatus("processing");
    setResult(null);
    setProgressStage(0);
    tickCountRef.current = 0;

    stageIntervalRef.current = setInterval(() => {
      setProgressStage((s) => (s < PROGRESS_STEPS.length - 2 ? s + 1 : s));
    }, 900);

    try {
      // ---- MOCK CALL (swap for the real fetch below when backend is ready) ----
    //  const data = await mockGradeRequest(file);
       const formData = new FormData();
      formData.append("student_pdf", file);
       formData.append("answer_key", JSON.stringify(SAMPLE_ANSWER_KEY));
       const res = await fetch(`${API_BASE}/grade`, { method: "POST", body: formData });
       const data = await res.json();

      setJobId(data.job_id);
      pollResult(data.job_id);
    } catch (err) {
      clearInterval(stageIntervalRef.current);
      setStatus("failed");
      setErrorMsg(err.message);
    }
  };

  /* ---- "GET /result/{job_id}" (mocked), polled  */
  const pollResult = useCallback((id) => {
    const poll = async () => {
      try {
        //  MOCK CALL  ----
       // const data = await mockPollResult(id, tickCountRef.current, file?.name);
         const res = await fetch(`${API_BASE}/result/${id}`);
         const data = await res.json();

        tickCountRef.current += 1;

        if (data.status === "graded" || data.status === "review_needed") {
          clearInterval(stageIntervalRef.current);
          setProgressStage(PROGRESS_STEPS.length - 1);
          setResult(data);
          setStatus(data.status);
        } else if (data.status === "failed") {
          clearInterval(stageIntervalRef.current);
          setStatus("failed");
          setErrorMsg(data.error || "Grading failed.");
        } else {
          pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        clearInterval(stageIntervalRef.current);
        setStatus("failed");
        setErrorMsg(err.message);
      }
    };
    pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS);
  }, [file]);

  useEffect(() => {
    return () => {
      clearTimeout(pollTimeoutRef.current);
      clearInterval(stageIntervalRef.current);
    };
  }, []);

  const breakdown = result?.breakdown || [];
  const strengths = breakdown.filter((q) => q.score === q.max_score);
  const mistakes = breakdown.filter((q) => q.score < q.max_score);
  const gradeLetter = result?.grade || "-";

  return (
    <div className="min-h-screen w-full bg-[#F7F8FA] text-slate-800 font-sans px-4 sm:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Mock mode banner */}
        <div className="flex items-center gap-2 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2 mb-5 w-fit">
          <Sparkles size={14} /> Mock mode — no backend required. Responses are dummy data.
        </div>

        {/* Header */}
        <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Assignment Evaluation</h1>
            <p className="text-sm text-slate-400 mt-1">
              Upload a student PDF to grade it against the configured answer key.
            </p>
          </div>
          {status !== "idle" && (
            <span
              className={`flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-full shrink-0 ${
                status === "graded"
                  ? "bg-green-50 text-green-600"
                  : status === "review_needed"
                  ? "bg-amber-50 text-amber-600"
                  : status === "failed"
                  ? "bg-red-50 text-red-600"
                  : "bg-blue-50 text-blue-600"
              }`}
            >
              {status === "graded" && <CheckCircle2 size={16} />}
              {status === "review_needed" && <AlertTriangle size={16} />}
              {status === "failed" && <AlertTriangle size={16} />}
              {status === "processing" && <Loader2 size={16} className="animate-spin" />}
              {status === "graded" && "Evaluation Completed"}
              {status === "review_needed" && "Flagged for Teacher Review"}
              {status === "failed" && "Grading Failed"}
              {status === "processing" && "Evaluating..."}
            </span>
          )}
        </div>

        {/* Upload card */}
        <Card className="mb-5">
          <CardHeader icon={FileText} iconClass="text-blue-500" title="Uploaded File" />

          {!file ? (
            <label
              htmlFor="pdf-upload"
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-200 rounded-xl py-10 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
            >
              <UploadCloud size={28} className="text-slate-400" />
              <span className="text-sm font-medium text-slate-600">Click to upload a PDF</span>
              <span className="text-xs text-slate-400">PDF only, up to 20MB</span>
              <input
                id="pdf-upload"
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleFileSelect}
              />
            </label>
          ) : (
            <div className="flex items-center gap-3 border border-slate-200 rounded-xl p-3">
              <div className="w-10 h-12 rounded-md bg-red-500 flex items-center justify-center text-white shrink-0">
                <FileText size={20} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-slate-800 truncate">{file.name}</div>
                <div className="text-xs text-slate-400">{formatBytes(file.size)}</div>
              </div>
              {!isBusy && (
                <>
                  <button title="Preview" onClick={() => window.open(URL.createObjectURL(file), "_blank")}>
                    <Eye size={16} className="text-slate-400 hover:text-slate-600" />
                  </button>
                  <button title="Remove" onClick={resetAll}>
                    <Trash2 size={16} className="text-slate-400 hover:text-red-500" />
                  </button>
                </>
              )}
            </div>
          )}

          {errorMsg && (
            <div className="flex items-center gap-1.5 text-xs text-red-600 mt-3">
              <AlertTriangle size={14} /> {errorMsg}
            </div>
          )}

          <div className="flex gap-3 mt-4">
            {file && !isBusy && !isDone && (
              <button
                onClick={startGrading}
                className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg py-2.5 px-5"
              >
                <Sparkles size={15} /> Start Grading
              </button>
            )}
            {file && !isBusy && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 border border-slate-200 rounded-lg py-2.5 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw size={14} /> Replace File
              </button>
            )}
            {isDone && (
              <button
                onClick={resetAll}
                className="flex items-center gap-2 border border-slate-200 rounded-lg py-2.5 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <UploadCloud size={14} /> Grade Another
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>
        </Card>

        {/* Processing state */}
        {isBusy && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">
            <ProgressStepper stage={progressStage} done={false} />
            <Card className="xl:col-span-2 flex items-center justify-center text-slate-400 text-sm">
              Simulating <code className="mx-1 text-slate-600">GET /result/{jobId}</code> poll #
              {tickCountRef.current + 1}...
            </Card>
          </div>
        )}

        {/* Failed state */}
        {status === "failed" && (
          <Card className="mb-5 border-red-200">
            <div className="flex items-center gap-2 text-red-600 font-semibold mb-1">
              <AlertTriangle size={18} /> Grading failed
            </div>
            <p className="text-sm text-slate-500">{errorMsg}</p>
          </Card>
        )}

        {/* review_needed */}
        {status === "review_needed" && (
          <Card className="mb-5 border-amber-200">
            <div className="flex items-center gap-2 text-amber-600 font-semibold mb-1">
              <AlertTriangle size={18} /> Flagged for teacher review
            </div>
            <p className="text-sm text-slate-500">{result?.reason}</p>
          </Card>
        )}

        {/* Graded results */}
        {status === "graded" && result && (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">
              <ProgressStepper stage={PROGRESS_STEPS.length - 1} done />

              <Card>
                <h3 className="font-semibold text-[15px] mb-4">Score Summary</h3>
                <div className="grid grid-cols-2 gap-4 items-center">
                  <div>
                    <ScoreRing percentage={result.percentage} />
                    <p className="text-center text-sm font-semibold text-slate-600 mt-2">
                      {result.total_score} / {result.max_score} marks
                    </p>
                  </div>
                  <div className="flex flex-col gap-3.5">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs text-slate-400">
                        <Star size={14} /> Grade
                      </span>
                      <span className="font-bold text-sm">{gradeLetter}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs text-slate-400">
                        <Clock size={14} /> Graded At
                      </span>
                      <span className="font-bold text-sm">
                        {result.graded_at ? new Date(result.graded_at).toLocaleTimeString() : "-"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs text-slate-400">
                        <Gauge size={14} /> Reliability
                      </span>
                      <span className="font-bold text-sm">{result.reliability_score}%</span>
                    </div>
                  </div>
                </div>
                <div className="mt-5">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Reliability ({result.reliability_level})</span>
                    <span
                      className={`font-semibold px-2 py-0.5 rounded-full text-[11px] ${pillColor(
                        result.reliability_level
                      )}`}
                    >
                      {result.reliability_level}
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full"
                      style={{ width: `${result.reliability_score}%` }}
                    />
                  </div>
                  {result.reliability_message && (
                    <p className="text-xs text-slate-400 mt-2">{result.reliability_message}</p>
                  )}
                </div>
              </Card>

              <Card>
                <h3 className="font-semibold text-[15px] mb-4">Actions</h3>
                <div className="flex flex-col gap-3">
                  <button
                    onClick={() => alert("Mock mode: no real PDF to download.")}
                    className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg py-2.5"
                  >
                    <Download size={15} /> Download Graded PDF
                  </button>
                  <button
                    onClick={resetAll}
                    className="flex items-center justify-center gap-2 border border-slate-200 rounded-lg py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <UploadCloud size={15} /> Submit Another
                  </button>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
              <Card>
                <CardHeader icon={ThumbsUp} iconClass="text-green-500" title="Full-Marks Questions" />
                {strengths.length === 0 ? (
                  <p className="text-sm text-slate-400">No full-marks questions this time.</p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {strengths.map((q) => (
                      <li key={q.question} className="flex items-start gap-2 text-sm text-slate-600">
                        <CheckCircle2 size={16} className="text-green-500 shrink-0 mt-0.5" />
                        <span>
                          <span className="font-semibold">{q.question}</span> — {q.feedback}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card>
                <CardHeader
                  icon={AlertTriangle}
                  iconClass="text-red-500"
                  title={`Mistakes Found (${mistakes.length})`}
                  titleClass="text-red-500"
                />
                <div className="flex flex-col gap-4">
                  {mistakes.map((q) => (
                    <div key={q.question} className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="text-sm font-semibold text-slate-700">{q.question}</span>{" "}
                        <span className="text-sm text-slate-500">{q.feedback}</span>
                        {q.spelling_mistakes?.length > 0 && (
                          <div className="text-xs text-red-400 mt-1">
                            Spelling: {q.spelling_mistakes.join(", ")}
                          </div>
                        )}
                      </div>
                      <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 shrink-0">
                        {q.score}/{q.max_score}
                      </span>
                    </div>
                  ))}
                  {mistakes.length === 0 && (
                    <p className="text-sm text-slate-400">No mistakes found. Perfect score!</p>
                  )}
                </div>
              </Card>

              <Card>
                <CardHeader icon={Grid3x3} iconClass="text-indigo-500" title="Question Breakdown" />
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                      <th className="font-medium pb-2">Q</th>
                      <th className="font-medium pb-2 text-center">Type</th>
                      <th className="font-medium pb-2 text-center">Score</th>
                      <th className="font-medium pb-2 text-right">Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {breakdown.map((q) => (
                      <tr key={q.question} className="border-b border-slate-50 last:border-0">
                        <td className="py-2.5 text-slate-600">{q.question}</td>
                        <td className="py-2.5 text-center text-slate-500">{q.type}</td>
                        <td className="py-2.5 text-center font-semibold text-slate-700">
                          {q.score}/{q.max_score}
                        </td>
                        <td className="py-2.5 text-right text-slate-500">{q.annotation_level || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
