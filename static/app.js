const form = document.getElementById("analysis-form");
const statusEl = document.getElementById("status");
const resultsGrid = document.getElementById("results-grid");
const analyzeBtn = document.getElementById("analyze-btn");

const outputFields = {
  job_analysis: document.getElementById("job_analysis"),
  resume_match: document.getElementById("resume_match"),
  updated_cv: document.getElementById("updated_cv"),
  cover_letter: document.getElementById("cover_letter"),
  scoring: document.getElementById("scoring"),
};

const SECTION_LABELS = {
  must_have: "Must Have",
  nice_to_have: "Nice To Have",
  keywords: "Keywords",
  responsibilities: "Responsibilities",
  notes: "Notes",
  matched: "Matched",
  missing: "Missing",
  weak_sections: "Weak Sections",
  risky_claims: "Risky Claims",
  action_items: "Action Items",
  overall: "Overall Score",
  components: "Component Scores",
  top_changes: "Top Changes",
};

const SECTION_ORDER = {
  "job-analysis": ["must_have", "nice_to_have", "responsibilities", "keywords", "notes"],
  "resume-match": ["matched", "missing", "weak_sections", "risky_claims", "action_items"],
  scoring: ["overall", "components", "top_changes", "notes"],
};

const BADGE_LIST_KEYS = new Set(["keywords"]);

function stripCodeFences(text) {
  const source = String(text ?? "").trim();
  const match = source.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  return match ? match[1].trim() : source;
}

function normalizeCommonLlmJsonIssues(text) {
  const source = String(text ?? "")
    .replaceAll("\u201c", '"')
    .replaceAll("\u201d", '"')
    .replaceAll("\u2018", "'")
    .replaceAll("\u2019", "'");

  let inString = false;
  let escaped = false;
  let out = "";

  for (const ch of source) {
    if (escaped) {
      out += ch;
      escaped = false;
      continue;
    }

    if (ch === "\\") {
      out += ch;
      escaped = true;
      continue;
    }

    if (ch === '"') {
      out += ch;
      inString = !inString;
      continue;
    }

    if (inString && ch === "\n") {
      out += "\\n";
      continue;
    }

    if (inString && ch === "\r") {
      continue;
    }

    out += ch;
  }

  return out;
}

function parseNestedJson(text, maxDepth = 2) {
  let current = stripCodeFences(text);
  for (let depth = 0; depth <= maxDepth; depth += 1) {
    const candidates = [current, normalizeCommonLlmJsonIssues(current)];
    let parsed = null;

    try {
      parsed = JSON.parse(candidates[0]);
    } catch {
      try {
        parsed = JSON.parse(candidates[1]);
      } catch {
        return null;
      }
    }

    if (typeof parsed !== "string") {
      return parsed;
    }

    current = stripCodeFences(parsed);
  }
  return null;
}

function sanitizeProse(value) {
  if (value == null) {
    return "";
  }
  const source = stripCodeFences(String(value));
  return source.replace(/\*\*(.*?)\*\*/g, "$1").replace(/\r\n/g, "\n").trim();
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toSectionLabel(key) {
  if (SECTION_LABELS[key]) {
    return SECTION_LABELS[key];
  }

  return String(key)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function renderInlineValue(value) {
  if (value == null) {
    return "";
  }
  if (typeof value === "string") {
    return sanitizeProse(value);
  }
  return String(value);
}

function renderValueAsLines(value, indent = "") {
  if (Array.isArray(value)) {
    const lines = [];
    for (const item of value) {
      if (item && typeof item === "object") {
        lines.push(`${indent}-`);
        lines.push(...renderValueAsLines(item, `${indent}  `));
      } else {
        lines.push(`${indent}- ${renderInlineValue(item)}`);
      }
    }
    return lines;
  }

  if (value && typeof value === "object") {
    const lines = [];
    for (const [key, nested] of Object.entries(value)) {
      if (nested && typeof nested === "object") {
        lines.push(`${indent}${toSectionLabel(key)}:`);
        lines.push(...renderValueAsLines(nested, `${indent}  `));
      } else {
        lines.push(`${indent}${toSectionLabel(key)}: ${renderInlineValue(nested)}`);
      }
    }
    return lines;
  }

  return [`${indent}${renderInlineValue(value)}`];
}

function renderStructuredSections(value, sectionKind = "") {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  const lines = [];
  const priorityOrder = SECTION_ORDER[sectionKind] || [];
  const remainingKeys = new Set(Object.keys(value));

  for (const key of priorityOrder) {
    if (!(key in value)) {
      continue;
    }
    remainingKeys.delete(key);

    const sectionValue = value[key];
    if (sectionValue == null || sectionValue === "") {
      continue;
    }

    if (lines.length > 0) {
      lines.push("");
    }

    if (key === "overall" && (typeof sectionValue === "number" || typeof sectionValue === "string")) {
      lines.push(`${toSectionLabel(key)}: ${sectionValue}/100`);
      continue;
    }

    lines.push(`${toSectionLabel(key)}:`);
    lines.push(...renderValueAsLines(sectionValue, "  "));
  }

  for (const key of remainingKeys) {
    const sectionValue = value[key];
    if (sectionValue == null || sectionValue === "") {
      continue;
    }

    if (lines.length > 0) {
      lines.push("");
    }

    lines.push(`${toSectionLabel(key)}:`);
    lines.push(...renderValueAsLines(sectionValue, "  "));
  }

  return lines.join("\n");
}

function renderAnyHtml(value) {
  if (value == null || value === "") {
    return "";
  }

  if (Array.isArray(value)) {
    const items = value
      .map((item) => `<li>${renderAnyHtml(item)}</li>`)
      .join("");
    return `<ul class="result-list">${items}</ul>`;
  }

  if (value && typeof value === "object") {
    const rows = Object.entries(value)
      .map(([key, nested]) => {
        if (nested && typeof nested === "object") {
          return `<div class="kv-row"><div class="kv-key">${escapeHtml(toSectionLabel(key))}</div><div class="kv-value">${renderAnyHtml(nested)}</div></div>`;
        }
        return `<div class="kv-row"><div class="kv-key">${escapeHtml(toSectionLabel(key))}</div><div class="kv-value">${escapeHtml(renderInlineValue(nested))}</div></div>`;
      })
      .join("");
    return `<div class="kv-grid">${rows}</div>`;
  }

  return escapeHtml(renderInlineValue(value));
}

function renderSectionBodyHtml(sectionValue, key) {
  if (key === "overall" && (typeof sectionValue === "number" || typeof sectionValue === "string")) {
    const score = escapeHtml(sectionValue);
    return `<div class="score-pill">${score}<span>/100</span></div>`;
  }

  if (Array.isArray(sectionValue)) {
    if (BADGE_LIST_KEYS.has(key)) {
      const chips = sectionValue
        .map((item) => `<span class="chip">${escapeHtml(renderInlineValue(item))}</span>`)
        .join("");
      return `<div class="chip-wrap">${chips}</div>`;
    }

    const items = sectionValue
      .map((item) => `<li>${renderAnyHtml(item)}</li>`)
      .join("");
    return `<ul class="result-list">${items}</ul>`;
  }

  if (sectionValue && typeof sectionValue === "object") {
    return renderAnyHtml(sectionValue);
  }

  return `<p class="section-note">${escapeHtml(renderInlineValue(sectionValue))}</p>`;
}

function renderStructuredHtml(value, sectionKind = "") {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return "";
  }

  const priorityOrder = SECTION_ORDER[sectionKind] || [];
  const remainingKeys = new Set(Object.keys(value));
  const sections = [];

  for (const key of priorityOrder) {
    if (!(key in value)) {
      continue;
    }
    remainingKeys.delete(key);

    const sectionValue = value[key];
    if (sectionValue == null || sectionValue === "") {
      continue;
    }

    sections.push(
      `<section class="result-section">
        <h4>${escapeHtml(toSectionLabel(key))}</h4>
        ${renderSectionBodyHtml(sectionValue, key)}
      </section>`
    );
  }

  for (const key of remainingKeys) {
    const sectionValue = value[key];
    if (sectionValue == null || sectionValue === "") {
      continue;
    }

    sections.push(
      `<section class="result-section">
        <h4>${escapeHtml(toSectionLabel(key))}</h4>
        ${renderSectionBodyHtml(sectionValue, key)}
      </section>`
    );
  }

  return `<div class="structured-output">${sections.join("")}</div>`;
}

function proseToHtml(value) {
  const text = sanitizeProse(value);
  if (!text) {
    return "";
  }

  const paragraphs = text
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => `<p>${escapeHtml(block).replaceAll("\n", "<br>")}</p>`)
    .join("");

  return `<div class="prose-output">${paragraphs}</div>`;
}

function normalizeJsonLike(value) {
  if (typeof value === "string") {
    const parsed = parseNestedJson(value);
    if (parsed !== null) {
      return parsed;
    }
    return stripCodeFences(value);
  }

  if (value && typeof value === "object" && typeof value.raw_output === "string") {
    const recovered = parseNestedJson(value.raw_output);
    if (recovered !== null) {
      return recovered;
    }
  }

  return value;
}

function formatValue(value, mode = "json") {
  if (mode === "prose") {
    return sanitizeProse(value);
  }

  const normalized = normalizeJsonLike(value);
  if (typeof normalized === "string") {
    return normalized;
  }

  if (mode === "job-analysis" || mode === "resume-match" || mode === "scoring") {
    const rendered = renderStructuredSections(normalized, mode);
    if (rendered) {
      return rendered;
    }
  }

  try {
    return JSON.stringify(normalized, null, 2);
  } catch (err) {
    return String(normalized);
  }
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#8f1f1f" : "";
}

function setOutput(element, value, mode = "json") {
  const normalized = normalizeJsonLike(value);

  if (mode === "prose") {
    element.innerHTML = proseToHtml(normalized);
    return;
  }

  if (mode === "job-analysis" || mode === "resume-match" || mode === "scoring") {
    const html = renderStructuredHtml(normalized, mode);
    if (html) {
      element.innerHTML = html;
      return;
    }
  }

  if (typeof normalized === "string") {
    element.innerHTML = `<div class="prose-output"><p>${escapeHtml(normalized).replaceAll("\n", "<br>")}</p></div>`;
    return;
  }

  try {
    element.innerHTML = `<pre class="fallback-json">${escapeHtml(JSON.stringify(normalized, null, 2))}</pre>`;
  } catch {
    element.innerHTML = `<div class="prose-output"><p>${escapeHtml(String(normalized))}</p></div>`;
  }
}

function clearResults() {
  for (const el of Object.values(outputFields)) {
    el.innerHTML = "";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResults();
  resultsGrid.hidden = true;

  const payload = {
    job_description: form.job_description.value.trim(),
    cv_text: form.cv_text.value.trim(),
    target_role: form.target_role.value.trim(),
  };

  if (!payload.job_description || !payload.cv_text) {
    setStatus("Please provide both job description and CV text.", true);
    return;
  }

  analyzeBtn.disabled = true;
  setStatus("Running full analysis...");

  try {
    const response = await fetch("/api/full-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed with status ${response.status}`);
    }

    setOutput(outputFields.job_analysis, data.job_analysis, "job-analysis");
    setOutput(outputFields.resume_match, data.resume_match, "resume-match");
    setOutput(outputFields.updated_cv, data.updated_cv, "prose");
    setOutput(outputFields.cover_letter, data.cover_letter, "prose");
    setOutput(outputFields.scoring, data.scoring, "scoring");

    resultsGrid.hidden = false;
    setStatus("Analysis complete.");
  } catch (error) {
    setStatus(error.message || "Unexpected error while running analysis.", true);
  } finally {
    analyzeBtn.disabled = false;
  }
});
