# S12-R-001 — Repository Owner Actions Document

This document outlines the manual configurations that must be performed by a GitHub Repository Owner to finalize the baseline security gates.

## 1. Switch Default Branch to `main`

1. Open your repository on GitHub.
2. Navigate to **Settings** > **Branches**.
3. Under the **Default branch** section, click the switch button (two opposing arrows) next to the current default branch.
4. Select `main` from the dropdown list.
5. Click **Update**.
6. Review the warning regarding changes to local clones and PRs, then click **I understand, update the default branch**.

## 2. Configure Branch Protection Rules for `main`

1. On the same **Settings** > **Branches** page, go to the **Branch protection rules** section.
2. Click **Add branch protection rule**.
3. In the **Branch name pattern** field, enter `main`.
4. Enable the following checkboxes:
   - **Require a pull request before merging**:
     - Set **Required approvals** to `1` (or your team's standard requirement).
   - **Require status checks to pass before merging**:
     - Check **Require branches to be up to date before merging**.
     - Under the search box for status checks, search for and select the following job names matching the CI workflow:
       - `backend`
       - `worker`
       - `frontend`
   - **Require conversation resolution before merging**:
     - Check **Require conversation resolution before merging** to ensure all comment threads are resolved.
   - **Block force pushes**:
     - Ensure **Block force pushes** is checked (this is enabled by default to prevent overriding history).
   - **Block deletion**:
     - Ensure **Restrict deletions** is checked (this is enabled by default to prevent deleting `main`).
5. Click **Create** (or **Save changes** at the bottom).
6. Authenticate with your GitHub password or 2FA if prompted.

## 3. Verification Steps

To verify the setup:
1. Try to push directly to `main` from your local machine. It should be blocked with an error message: `protected branch hook declined`.
2. Open a Pull Request. Ensure that the checks named `backend`, `worker`, and `frontend` start running automatically and that merging is blocked until they complete successfully.
