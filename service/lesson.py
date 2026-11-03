"""Shared teacher-led lesson workspace. No inference or generated example data."""
import json
from fastapi import Header, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Step(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    duration: str = Field(max_length=40)
    goal: str = Field(max_length=1000)
    tips: list[str] = Field(max_length=10)

    @field_validator("title")
    @classmethod
    def title_present(cls, value):
        if not value.strip():
            raise ValueError("step title required")
        return value

    @field_validator("tips")
    @classmethod
    def tip_bounds(cls, values):
        if any(not value.strip() or len(value) > 400 for value in values):
            raise ValueError("invalid tip")
        return values


class Notebook(StrictModel):
    chords: list[str] = Field(max_length=64)
    notation: str = Field(max_length=8000)
    tabs: str = Field(max_length=8000)

    @field_validator("chords")
    @classmethod
    def chord_bounds(cls, values):
        if any(not value.strip() or len(value) > 32 for value in values):
            raise ValueError("invalid chord")
        return values


class LessonUpdate(StrictModel):
    revision: int = Field(ge=0, le=2**53-2)
    plan: list[Step] = Field(max_length=32)
    step: int | None
    notebook: Notebook

    @model_validator(mode="after")
    def current_step_exists(self):
        if ((self.plan and (self.step is None or not 0 <= self.step < len(self.plan)))
                or (not self.plan and self.step is not None)):
            raise ValueError("current step must belong to plan")
        return self


def empty_lesson():
    return {"revision": 0, "plan": [], "step": None,
            "notebook": {"chords": [], "notation": "", "tabs": ""}}


def register_routes(app, db, commit, authenticate, find_session, audit, err):
    def load(c, sid):
        row = c.execute("SELECT revision,content FROM lesson_workspaces WHERE session_id=?", (sid,)).fetchone()
        if not row:
            return empty_lesson()
        # Revalidate persisted state too; corruption cannot become a worksheet.
        return LessonUpdate(revision=row["revision"], **json.loads(row["content"])).model_dump()

    @app.get("/sessions/{sid}/lesson")
    def read_lesson(sid: str, request: Request, authorization: str = Header(default="")):
        _, failure = authenticate(authorization, request)
        if failure is not None:
            return failure
        c = db()
        try:
            if not find_session(c, sid, request):
                return err(404, "session_not_found")
            try:
                return load(c, sid)
            except (ValueError, TypeError):
                return err(503, "lesson_unavailable")
        finally:
            c.close()

    @app.post("/sessions/{sid}/lesson")
    def write_lesson(sid: str, body: LessonUpdate, request: Request, authorization: str = Header(default="")):
        actor, failure = authenticate(authorization, request)
        if failure is not None:
            return failure
        if actor != "maestro":
            return err(403, "maestro_required")
        proposed = body.model_dump(exclude={"revision"})
        content = json.dumps(proposed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(content.encode("utf-8")) > 28000:
            return err(422, "lesson_too_large")
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            meeting = find_session(c, sid, request)
            if not meeting:
                return err(404, "session_not_found")
            if meeting["state"] not in ("created", "active"):
                return err(409, "lesson_read_only")
            try:
                current = load(c, sid)
            except (ValueError, TypeError):
                return err(503, "lesson_unavailable")
            # An ambiguous/lost HTTP response can be replayed without another
            # revision or audit event. A different stale edit cannot overwrite.
            if proposed == {k: v for k, v in current.items() if k != "revision"}:
                return current
            if current["revision"] != body.revision:
                return err(409, "lesson_revision_conflict")
            revision = body.revision + 1
            c.execute("INSERT INTO lesson_workspaces(session_id,revision,content) VALUES(?,?,?) "
                      "ON CONFLICT(session_id) DO UPDATE SET revision=excluded.revision,content=excluded.content",
                      (sid, revision, content))
            audit(c, sid, "lesson_updated", str(revision), actor)
            commit(c)
            return {"revision": revision, **proposed}
        finally:
            c.close()
    return load  # Translation uses the identical validated workspace snapshot.
