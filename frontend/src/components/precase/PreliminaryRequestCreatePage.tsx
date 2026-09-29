import React, { FormEvent, useRef, useState } from "react";

import { ApiError } from "../../api/client";
import { createProject } from "../../api/projects";
import { APP_ROUTES, projectListVerificationPath } from "../../contracts/valoraV23";
import "./precase.css";

type SubmitState = "idle" | "submitting" | "uncertain" | "sessionExpired";

function knownCreateError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Không thể tạo yêu cầu sơ bộ. Vui lòng kiểm tra thông tin và thử lại.";
  }
  if (error.status === 401) return "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.";
  if (error.status === 403) return "Tài khoản chưa có quyền tạo yêu cầu sơ bộ.";
  if (error.status === 409) return "Mã hồ sơ đã tồn tại trong đơn vị. Vui lòng dùng mã khác.";
  if (error.status === 422) return "Thông tin yêu cầu sơ bộ chưa hợp lệ. Vui lòng kiểm tra lại.";
  return "Không thể tạo yêu cầu sơ bộ. Vui lòng kiểm tra thông tin và thử lại.";
}

export function PreliminaryRequestCreatePage({
  onNavigate,
  onSessionExpired,
}: {
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [feedback, setFeedback] = useState<string | null>(null);
  const submitLocked = useRef(false);
  const submittedCode = useRef<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitState !== "idle" || submitLocked.current) return;

    const normalizedCode = code.trim();
    const normalizedName = name.trim();
    if (!normalizedCode || !normalizedName) {
      setFeedback("Mã hồ sơ và tên yêu cầu sơ bộ là thông tin bắt buộc.");
      return;
    }

    setFeedback(null);
    submitLocked.current = true;
    submittedCode.current = normalizedCode;
    setSubmitState("submitting");
    try {
      await createProject({
        code: normalizedCode,
        name: normalizedName,
        description: description.trim() || null,
        customer_id: null,
      });
      onNavigate(APP_ROUTES.projectList);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFeedback(knownCreateError(error));
        setSubmitState("sessionExpired");
        return;
      }
      if (!(error instanceof ApiError) || error.status === 0 || error.status === 408 || error.status >= 500) {
        setFeedback(
          "Chưa xác định yêu cầu đã được tạo hay chưa. Hãy về danh sách hồ sơ để kiểm tra trước khi gửi lại."
        );
        setSubmitState("uncertain");
        return;
      }
      setFeedback(knownCreateError(error));
      submitLocked.current = false;
      setSubmitState("idle");
    }
  };

  const canSubmit = Boolean(code.trim() && name.trim()) && submitState === "idle";

  return (
    <main className="precase-create-page">
      <header className="precase-create-header">
        <p>Yêu cầu sơ bộ</p>
        <h1>Tạo yêu cầu sơ bộ</h1>
        <span>
          Bạn có thể tạo yêu cầu mà chưa gắn khách hàng. Cần gắn khách hàng trước khi chuyển sang
          thẩm định chính thức.
        </span>
      </header>

      <form aria-busy={submitState === "submitting"} className="precase-create-form valora-panel" onSubmit={submit}>
        <div className="valora-panel__header">Thông tin yêu cầu</div>
        <div className="valora-panel__body precase-create-fields">
          <label>
            Mã hồ sơ
            <input
              className="valora-field"
              disabled={submitState !== "idle"}
              maxLength={64}
              name="code"
              onChange={(event) => setCode(event.target.value)}
              placeholder="Ví dụ: SB-2026-001"
              required
              value={code}
            />
          </label>
          <label>
            Tên yêu cầu sơ bộ
            <input
              className="valora-field"
              disabled={submitState !== "idle"}
              maxLength={255}
              name="name"
              onChange={(event) => setName(event.target.value)}
              placeholder="Nhập tên hồ sơ hoặc tài sản cần thẩm định"
              required
              value={name}
            />
          </label>
          <label>
            Mô tả <span>(không bắt buộc)</span>
            <textarea
              className="valora-field precase-create-description"
              disabled={submitState !== "idle"}
              name="description"
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              value={description}
            />
          </label>

          {feedback && (
            <div
              className={`valora-message ${
                submitState === "uncertain" ? "valora-message--warning" : "valora-message--error"
              }`}
              id="precase-create-feedback"
              role="alert"
            >
              {feedback}
            </div>
          )}
        </div>
        <div className="valora-panel__footer precase-create-actions">
          {submitState === "uncertain" ? (
            <button
              className="valora-button valora-button--primary"
              onClick={() => onNavigate(projectListVerificationPath(submittedCode.current ?? code.trim()))}
              type="button"
            >
              Về danh sách hồ sơ để kiểm tra
            </button>
          ) : submitState === "sessionExpired" ? (
            <button
              className="valora-button valora-button--primary"
              onClick={() => {
                onSessionExpired();
                onNavigate(APP_ROUTES.projectList);
              }}
              type="button"
            >
              Đăng nhập lại
            </button>
          ) : (
            <>
              <button
                className="valora-button valora-button--secondary"
                disabled={submitState === "submitting"}
                onClick={() => onNavigate(APP_ROUTES.projectList)}
                type="button"
              >
                Hủy
              </button>
              <button
                className="valora-button valora-button--primary"
                disabled={!canSubmit}
                type="submit"
              >
                {submitState === "submitting" ? "Đang tạo…" : "Tạo yêu cầu sơ bộ"}
              </button>
            </>
          )}
        </div>
      </form>
    </main>
  );
}
