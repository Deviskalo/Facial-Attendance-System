from __future__ import annotations

import json
import threading
from typing import Any, Optional

import cv2
import numpy as np

from backend.config import (
    BLUR_MIN_VARIANCE,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    DET_SIZE,
    EMBEDDING_IDS_PATH,
    EMBEDDINGS_PATH,
    INSIGHTFACE_MODEL,
    INSIGHTFACE_PROVIDERS,
    MODELS_ROOT,
)
from backend.database import all_embeddings, get_all_settings, group_embeddings_by_employee

_lock = threading.Lock()
_app = None
_cache_ids: list[str] = []
_cache_vecs: Optional[np.ndarray] = None


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    vec = np.asarray(vec, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vec)) + 1e-8
    return vec / norm


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(l2_normalize(a), l2_normalize(b)))


def ensure_models() -> None:
    get_face_app()


def get_face_app():
    global _app
    if _app is not None:
        return _app
    with _lock:
        if _app is not None:
            return _app
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            root=str(MODELS_ROOT),
            providers=INSIGHTFACE_PROVIDERS,
        )
        app.prepare(ctx_id=-1, det_size=DET_SIZE)
        _app = app
        return _app


def decode_image(data: bytes) -> Optional[np.ndarray]:
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def brightness_score(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def blur_score(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def crop_face(frame: np.ndarray, bbox: np.ndarray, pad: float = 0.25) -> np.ndarray:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * pad))
    y1 = max(0, int(y1 - bh * pad))
    x2 = min(w, int(x2 + bw * pad))
    y2 = min(h, int(y2 + bh * pad))
    return frame[y1:y2, x1:x2]


def quality_audit(frame: np.ndarray, faces: list) -> dict[str, Any]:
    brightness = brightness_score(frame)
    blur = blur_score(frame)
    issues: list[str] = []
    if brightness < BRIGHTNESS_MIN:
        issues.append("Too dark — move toward a light source.")
    elif brightness > BRIGHTNESS_MAX:
        issues.append("Too bright — reduce glare or backlight.")
    if blur < BLUR_MIN_VARIANCE:
        issues.append("Image is blurry — hold still.")
    if len(faces) == 0:
        issues.append("No face detected.")
    elif len(faces) > 1:
        issues.append("Multiple faces in frame — keep only one person.")
    ok = not issues
    return {
        "ok": ok,
        "brightness": round(brightness, 1),
        "blur": round(blur, 1),
        "face_count": len(faces),
        "issues": issues,
    }


def detect_faces(frame: np.ndarray) -> list:
    app = get_face_app()
    return app.get(frame)


def analyze_frame(frame: np.ndarray) -> dict[str, Any]:
    faces = detect_faces(frame)
    quality = quality_audit(frame, faces)
    packed = []
    for face in faces:
        bbox = [int(v) for v in face.bbox.astype(int).tolist()]
        packed.append(
            {
                "bbox": bbox,
                "det_score": float(getattr(face, "det_score", 0.0)),
                "embedding": np.asarray(face.normed_embedding, dtype=np.float32)
                if getattr(face, "normed_embedding", None) is not None
                else np.asarray(face.embedding, dtype=np.float32),
            }
        )
    h, w = frame.shape[:2]
    return {"quality": quality, "faces": packed, "frame_size": [w, h]}


def matching_threshold() -> float:
    settings = get_all_settings()
    try:
        return float(settings.get("matching_threshold", "0.36"))
    except ValueError:
        return 0.36


def rebuild_match_cache() -> None:
    global _cache_ids, _cache_vecs
    grouped = group_embeddings_by_employee(active_only=True)
    ids: list[str] = []
    vecs: list[np.ndarray] = []
    for emp_id, embs in grouped.items():
        if not embs:
            continue
        stacked = np.stack([l2_normalize(v) for v in embs], axis=0)
        avg = l2_normalize(stacked.mean(axis=0))
        ids.append(emp_id)
        vecs.append(avg)
    _cache_ids = ids
    if vecs:
        _cache_vecs = np.stack(vecs, axis=0).astype(np.float32)
        np.save(EMBEDDINGS_PATH, _cache_vecs)
    else:
        _cache_vecs = np.zeros((0, 512), dtype=np.float32)
        np.save(EMBEDDINGS_PATH, _cache_vecs)
    EMBEDDING_IDS_PATH.write_text(json.dumps(ids), encoding="utf-8")


def load_match_cache() -> tuple[list[str], np.ndarray]:
    global _cache_ids, _cache_vecs
    if _cache_vecs is not None:
        return _cache_ids, _cache_vecs
    if EMBEDDINGS_PATH.exists() and EMBEDDING_IDS_PATH.exists():
        _cache_ids = json.loads(EMBEDDING_IDS_PATH.read_text(encoding="utf-8"))
        _cache_vecs = np.load(EMBEDDINGS_PATH)
        return _cache_ids, _cache_vecs
    rebuild_match_cache()
    return _cache_ids, _cache_vecs


def match_embedding(embedding: np.ndarray) -> dict[str, Any]:
    ids, matrix = load_match_cache()
    threshold = matching_threshold()
    vec = l2_normalize(embedding)
    if matrix is None or len(ids) == 0 or matrix.shape[0] == 0:
        return {
            "matched": False,
            "employee_id": None,
            "distance": 1.0,
            "confidence": 0.0,
            "threshold": threshold,
        }
    sims = matrix @ vec
    best_idx = int(np.argmax(sims))
    best_sim = float(sims[best_idx])
    distance = 1.0 - best_sim
    matched = distance < threshold
    return {
        "matched": matched,
        "employee_id": ids[best_idx] if matched else None,
        "nearest_employee_id": ids[best_idx],
        "distance": distance,
        "confidence": max(0.0, min(1.0, best_sim)),
        "threshold": threshold,
    }


def find_duplicate(embedding: np.ndarray, exclude_employee_id: Optional[str] = None) -> Optional[str]:
    threshold = matching_threshold()
    for emp_id, stored in all_embeddings(exclude_employee_id=exclude_employee_id):
        if cosine_distance(embedding, stored) < threshold:
            return emp_id
    return None


def preview_matches(embedding: np.ndarray, top_k: int = 3) -> list[dict[str, Any]]:
    ids, matrix = load_match_cache()
    vec = l2_normalize(embedding)
    if matrix is None or len(ids) == 0:
        return []
    sims = matrix @ vec
    order = np.argsort(-sims)[:top_k]
    out = []
    for idx in order:
        dist = float(1.0 - sims[int(idx)])
        out.append(
            {
                "employee_id": ids[int(idx)],
                "distance": dist,
                "would_match": dist < matching_threshold(),
            }
        )
    return out
