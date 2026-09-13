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
        <p className="login-eyebrow">VALORA · OPERATIONAL WORKSPACE</p>
        <h1 id="login-title">Mỗi hồ sơ bắt đầu từ một ngữ cảnh đáng tin cậy.</h1>
        <p>
          Đăng nhập vào đúng đơn vị để mở hồ sơ, kiểm tra lineage và làm việc với tài liệu
          OneDrive Personal đã được xác minh.
        </p>
        <div className="login-trust-note">
          <span>01</span>
          <p>Phiên làm việc dùng cookie bảo mật; mật khẩu và token không được lưu trên trình duyệt.</p>
        </div>
      </section>
      <form className="login-card" onSubmit={submit}>
        <header>
          <p>Truy cập hệ thống</p>
          <h2>Đăng nhập Valora</h2>
        </header>
        <label>
          Mã đơn vị
          <input
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
            autoComplete="current-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error && <div className="login-error" role="alert">{error}</div>}
        <button className="login-submit" disabled={submitting} type="submit">
          {submitting ? "Đang xác minh…" : "Đăng nhập"}
        </button>
        <small>Chỉ tài khoản đang hoạt động trong đúng đơn vị mới có thể tiếp tục.</small>
      </form>
    </main>
  );
}
