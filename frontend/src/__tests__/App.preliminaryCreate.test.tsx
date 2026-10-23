import React from "react";
import { act, create } from "react-test-renderer";
import { expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ session: {} as any, page: vi.fn() }));
vi.mock("../auth/SessionProvider", () => ({ SessionProvider: ({ children }: any) => children, useSession: () => mocks.session }));
vi.mock("../components/layout/AppShell", () => ({ AppShell: ({ children }: any) => <main>{children}</main> }));
vi.mock("../components/case-overview/useStageNavigation", () => ({ useStageNavigation: () => false }));
vi.mock("../components/precase/PreliminaryRequestCreatePage", () => ({ PreliminaryRequestCreatePage: (props: any) => { mocks.page(props); return <p>Create</p>; } }));
import { APP_ROUTES } from "../contracts/valoraV23";
import { AuthenticatedApp } from "../App";

it("A26 App supplies authenticated actor/tenant scope and keeps recovery reachable", async () => {
  mocks.session = { account: { id: crypto.randomUUID(), organization_id: crypto.randomUUID(), permissions: ["project:create"] }, logout: vi.fn(), restore: vi.fn() };
  vi.stubGlobal("window", { location: { hash: `#${APP_ROUTES.preliminaryRequestCreate}` }, addEventListener: vi.fn(), removeEventListener: vi.fn() });
  let root: any;
  await act(async () => { root = create(<AuthenticatedApp />); });
  expect(mocks.page.mock.calls[0][0].scope).toEqual({ organization_id: mocks.session.account.organization_id, actor_user_id: mocks.session.account.id });
  expect(JSON.stringify(root.toJSON())).toContain("Khôi phục yêu cầu sơ bộ");
});
