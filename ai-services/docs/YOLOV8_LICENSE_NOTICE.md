# Ultralytics YOLOv8 — license notice and academic-use record

**Status: ACADEMIC USE ONLY.** This record documents the license position for the
SmartProp graduation project. It is not a legal opinion and it does not waive any
obligation under AGPL-3.0.

---

## 1. What is used

| Component | Version | License | Where |
|---|---|---|---|
| `ultralytics` | 8.4.212 | **AGPL-3.0** | `ai-services/requirements-vision.txt` |
| `ultralytics-thop` | 2.2.5 | **AGPL-3.0** | transitive dependency |
| `ultralytics-platform` | 0.1.110 | **AGPL-3.0-only** | transitive dependency |
| `yolov8n.pt` (weights) | COCO pretrained, 6 549 796 B, sha256 prefix `f59b3d833e2f` | **AGPL-3.0** | `ai-services/var/vision/` (not in Git) |

Upstream project: <https://github.com/ultralytics/ultralytics>
License text: <https://www.gnu.org/licenses/agpl-3.0.html>

The checkpoint is the stock COCO-pretrained `yolov8n.pt`. **No retraining, no
fine-tuning, no custom weights.** The model is used as published by Ultralytics.

---

## 2. Declared scope of use

SmartProp is a **graduation project** used for study, research, and demonstration
to a mentor and an academic panel. Within this scope:

- The system runs on a local machine and on an isolated staging database.
- It is **not** offered as a commercial product.
- It is **not** published as a public network service.
- No fee is charged for access.
- No third party outside the project team is given access to the running system.

This scope is what keeps the project inside the "private use / academic
evaluation" situation. **It does not remove the license obligations** — it only
means those obligations are not currently triggered, because AGPL-3.0 attaches
them to distribution and to network interaction with users outside the
organisation.

---

## 3. What AGPL-3.0 actually requires

AGPL-3.0 is GPL-3.0 plus section 13. Two triggers matter here:

**Trigger A — distribution.** If a copy of the software is conveyed to someone
else, the recipient must receive the Corresponding Source under AGPL-3.0.

**Trigger B — network use (section 13).** If a modified version is made available
to users interacting with it **remotely over a network**, those users must be
offered the Corresponding Source.

For SmartProp, "Corresponding Source" would include at minimum:

- `ai-services/app/vision/` — the module that imports and calls Ultralytics;
- `ai-services/vision_main.py` — the service entrypoint;
- the backend code that calls the service
  (`PropertyImageAnalysisService`, `ImageAnalysisController`,
  `ImageAnalysisDtos`, `PropertyImageAnalysisRepository`);
- the build/run instructions needed to reproduce the service
  (`requirements-vision.txt`, startup script).

---

## 4. Obligations that apply even now

These are cheap and should simply be done:

1. **Keep the license notice.** Do not strip Ultralytics copyright headers from
   any file that carries them.
2. **State the dependency and its license** in project documentation — this file
   is that statement.
3. **Do not claim the model as the team's own work.** The valuation models
   (XGBoost V6/V1.3) are the team's research; YOLOv8n is a third-party pretrained
   model used as a component.
4. **Do not remove the AGPL notice from the installed package** if the runtime is
   ever redistributed.

---

## 5. What would trigger full obligations

If any of the following happens, the project must either comply with AGPL-3.0 or
obtain a commercial license from Ultralytics **before** that step:

| Action | Consequence |
|---|---|
| Deploying SmartProp to a public URL where outsiders can use image analysis | Section 13 applies → must offer Corresponding Source |
| Handing the built system to another team or a company | Distribution → must convey source under AGPL |
| Publishing the app on an app store or as a hosted product | Distribution / network use → AGPL applies |
| Selling access or bundling with a paid service | Commercial use → AGPL still applies; Enterprise License needed to keep source closed |

**Academic submission of source code to a university is not a trigger** — the
code is already being handed in as coursework, which is compatible with AGPL.

---

## 6. Options if the project later goes beyond academic use

| Option | What it means | Cost |
|---|---|---|
| **A. Stay academic** | Keep the current scope. No new obligation. | None |
| **B. Publish under AGPL** | Release the vision module (and the backend parts that call it) under AGPL-3.0. | Free, but source must be open |
| **C. Ultralytics Enterprise License** | Keep the source closed in a commercial product. | Paid, contact Ultralytics |
| **D. Replace the model** | Swap to a permissively licensed detector. | Engineering work; would require redoing the vision module |

**Current choice: A.** Recorded here at the team's request, for the graduation
project scope only.

---

## 7. Honest limits of this record

- This is a **project record**, not legal advice. A lawyer should review before
  any commercial step.
- "Academic use" is a description of the current deployment, **not a legal
  exemption**. AGPL-3.0 has no academic exemption clause.
- If the project is later published publicly, the obligations in section 5 apply
  regardless of the academic origin.
- The team has **not** been granted any exemption by Ultralytics. No such
  exemption has been requested.

---

## 8. Where this is referenced

- `ai-services/requirements-vision.txt` — install instructions and license note.
- `ai-services/app/vision/__init__.py` — package docstring.
- `ai-services/docs/YOLOV8_AUTOSCAN_INTEGRATION_CONTRACT.md` — integration design.
- `SMARTPROP_YOLOV8_FINAL_RELEASE_GATE.md` — release gate record.
