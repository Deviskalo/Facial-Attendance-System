# Attendance kiosk system plan
_Exported on 10/8/2026 at 15:10:32 MST from Cursor (3.23.23)_

---

**User**

Read @Attendance_Kiosk_System_Context.md and @Attendance_Kiosk_System_Folder_Structure.txt  to know what we're about to build and make a plan for it

---

**Cursor**

I'll read the context docs and switch to Plan mode so we can map the kiosk system before building.

Two stack choices change the whole build. I’ll lock those first, then write the plan.

**Architecture choices**

> **Which frontend should we use? Next.js needs Node.js plus Python (heavier one-click setup). Jinja2 + Tailwind keeps the whole stack Python-only, which matches the setup.bat / setup.sh installer better.**
> - FastAPI + Jinja2 + Tailwind (Python-only, simpler offline install) ✔
> - Next.js + Tailwind talking to FastAPI (two runtimes, richer UI)

> **Which face engine? insightface (ArcFace/ONNX) is more accurate but downloads larger models. face_recognition/dlib is simpler but dlib is painful to install on Windows.**
> - insightface + OpenCV (recommended: 512D embeddings, ONNX models in /models) ✔
> - face_recognition / dlib (128D embeddings)

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll start with scaffolding (folders, config, database, FastAPI + Jinja2) and work through the remaining todos until the kiosk is complete.

Scaffolding the Jinja templates, CSS, and kiosk/admin JS next so the FastAPI app has a full UI shell.

---


