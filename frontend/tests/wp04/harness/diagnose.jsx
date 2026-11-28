/**
 * WP-04 B4 — responsive diagnosis harness.
 *
 * Renders the panel and writes real layout measurements into the DOM so a headless browser dump
 * can be inspected without a DevTools client. Reports widths, computed styles, ancestor chain,
 * Tailwind rule presence and per-element clipping.
 */
import "../../../src/styles/style.css";
import "../../../src/styles/interface.css";
import { StrictMode, createElement as h } from "react";
import { createRoot } from "react-dom/client";

import { ValuationExplanationPanel } from "../../../src/features/prediction/ValuationExplanationPanel.js";
import samples from "../fixtures/explanation-samples.json";

const params = new URLSearchParams(window.location.search);
const state = params.get("state") || "technical";
const forcedWidth = Number(params.get("width")) || 0;
if (forcedWidth) {
  document.documentElement.style.width = `${forcedWidth}px`;
  document.body.style.width = `${forcedWidth}px`;
  document.body.style.margin = "0";
}


function panel() {
  return h(ValuationExplanationPanel, {
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
    modelVersion: "v1.3",
  });
}

function App() {
  return h("main", null, panel());
}

function rulePresence() {
  const wanted = [".w-full", ".min-w-0", ".table-fixed", ".flex", ".overflow-hidden"];
  const found = {};
  for (const sheet of Array.from(document.styleSheets)) {
    let rules;
    try {
      rules = Array.from(sheet.cssRules || []);
    } catch {
      continue;
    }
    for (const rule of rules) {
      const text = rule.cssText || "";
      for (const selector of wanted) {
        if (text.includes(`${selector} `) || text.includes(`${selector}{`) || text.includes(`${selector},`)) {
          found[selector] = true;
        }
      }
    }
  }
  return wanted.map((selector) => `${selector}=${found[selector] ? "yes" : "NO"}`).join("|");
}

function ancestorChain(node) {
  const chain = [];
  let current = node;
  while (current && current !== document.documentElement.parentNode) {
    const rect = current.getBoundingClientRect();
    chain.push(
      `${current.tagName.toLowerCase()}${current.id ? `#${current.id}` : ""}` +
        `[w=${Math.round(rect.width)} sw=${current.scrollWidth} cw=${current.clientWidth}` +
        ` ov=${getComputedStyle(current).overflowX}]`,
    );
    current = current.parentElement;
  }
  return chain.join(" > ");
}

function measure() {
  const section = document.querySelector('[data-testid="valuation-explanation-panel"]');
  const table = document.querySelector('[data-testid="explanation-waterfall"]');
  const groupValues = Array.from(document.querySelectorAll("[data-direction]")).map((row) => {
    const value = row.lastElementChild;
    const rect = value?.getBoundingClientRect();
    return {
      text: value?.textContent?.trim() || "",
      right: rect ? Math.round(rect.right) : null,
      width: rect ? Math.round(rect.width) : null,
      visible: rect ? rect.right <= section.getBoundingClientRect().right + 1 : null,
    };
  });
  const cells = Array.from(document.querySelectorAll("table th, table td")).map((cell) => {
    const rect = cell.getBoundingClientRect();
    return {
      text: (cell.textContent || "").trim().slice(0, 24),
      right: Math.round(rect.right),
      clipped: rect.right > section.getBoundingClientRect().right + 1,
    };
  });

  if (section?.querySelector("details")) {
    section.querySelector("details").open = true;
  }

  const sectionRect = section?.getBoundingClientRect();
  return {
    viewport: {
      innerWidth: window.innerWidth,
      docClient: document.documentElement.clientWidth,
      docScroll: document.documentElement.scrollWidth,
      bodyScroll: document.body.scrollWidth,
    },
    tailwind: rulePresence(),
    ancestors: ancestorChain(section),
    section: sectionRect
      ? {
          width: Math.round(sectionRect.width),
          left: Math.round(sectionRect.left),
          right: Math.round(sectionRect.right),
          clientWidth: section.clientWidth,
          scrollWidth: section.scrollWidth,
          overflowX: getComputedStyle(section).overflowX,
          maxWidth: getComputedStyle(section).maxWidth,
          minWidth: getComputedStyle(section).minWidth,
          display: getComputedStyle(section).display,
          boxSizing: getComputedStyle(section).boxSizing,
          padding: getComputedStyle(section).padding,
        }
      : null,
    table: table
      ? {
          width: Math.round(table.getBoundingClientRect().width),
          scrollWidth: table.scrollWidth,
          clientWidth: table.clientWidth,
          tableLayout: getComputedStyle(table).tableLayout,
        }
      : null,
    groupValues,
    clippedCells: cells.filter((cell) => cell.clipped),
    cellCount: cells.length,
  };
}

createRoot(document.getElementById("root")).render(h(StrictMode, null, h(App)));

requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    const data = measure();
    document.documentElement.dataset.diag = "ready";
    const pre = document.createElement("pre");
    pre.id = "diag";
    pre.textContent = JSON.stringify(data);
    document.body.appendChild(pre);
    document.title = `diag-${window.innerWidth}`;
  });
});

export { state };
