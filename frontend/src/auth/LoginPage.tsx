import React, { FormEvent, useState } from "react";

import { useSession } from "./SessionProvider";
import "./session.css";

export function LoginPage() {
  const { login, error } = useSession();
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await login({
        organization_slug: organizationSlug.trim(),
        email: email.trim(),
        password,
      });
    } catch {
      // SessionProvider owns the sanitized error presentation.
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-intro" aria-labelledby="login-title">
        <p className="login-eyebrow">VALORA</p>
        <h1 id="login-title">Không gian làm việc thẩm định giá</h1>
        <p>
          Đăng nhập vào đúng đơn vị để mở hồ sơ, tiếp tục công việc và truy cập Không gian tài liệu.
        </p>
        <div className="login-trust-note">
          <strong>Bảo vệ phiên làm việc</strong>
          <p>Phiên làm việc dùng cookie bảo mật; mật khẩu và token không được ứng dụng lưu trong trình duyệt.</p>
        </div>
      </section>
      <form aria-describedby={error ? "login-error" : undefined} className="login-card valora-panel" onSubmit={submit}>
        <header>
          <p>Truy cập hệ thống</p>
          <h2>Đăng nhập Valora</h2>
        </header>
        <label>
          Mã đơn vị
          <input
            className="valora-field"
            autoComplete="organization"
            name="organization_slug"
            onChange={(event) => setOrganizationSlug(event.target.value)}
            placeholder="vi-du: chi-nhanh-gia-lai"
            required
            value={organizationSlug}
          />
        </label>
        <label>
          Email
          <input
            className="valora-field"
            autoComplete="email"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="ten@donvi.vn"
            required
            type="email"
            value={email}
          />
        </label>
        <label>
          Mật khẩu
          <input
            className="valora-field"
            autoComplete="current-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error && <div className="login-error valora-message valora-message--error" id="login-error" role="alert">{error}</div>}
        <button className="login-submit valora-button valora-button--primary" disabled={submitting} type="submit">
          {submitting ? "Đang xác minh…" : "Đăng nhập"}
        </button>
        <small>Chỉ tài khoản đang hoạt động trong đúng đơn vị mới có thể tiếp tục.</small>
      </form>
    </main>
  );
}
