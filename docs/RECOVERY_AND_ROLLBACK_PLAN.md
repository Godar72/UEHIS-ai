# UEHIS — Recovery, Pull Request, and Rollback Plan

**Branch Name:** `recovery/aws-authoritative-reconstruction`
**Base Target:** `origin/main`
**Repository:** `https://github.com/Godar72/UEHIS-ai.git`

---

## 1. Production Safety and Workspace Isolation

In accordance with strict safety mandates:
- **No changes have been pushed to GitHub `main`**.
- **No production containers on AWS were stopped, restarted, or rebuilt during this audit**.
- **No production databases, Nginx routes, or DNS records were modified**.
- **The original workspace `C:\Users\adity\Desktop\SL` remains intact**.

---

## 2. Procedure for Reviewing and Merging the Recovery Branch

### Step 1: Push the Isolated Recovery Branch
From terminal, push only the recovery branch to GitHub:
```bash
git -C C:\Users\adity\Desktop\UEHIS-AWS-Recovery push origin recovery/aws-authoritative-reconstruction
```

### Step 2: Open GitHub Pull Request
1. Navigate to `https://github.com/Godar72/UEHIS-ai/pulls`.
2. Create PR:
   - Base branch: `main`
   - Compare branch: `recovery/aws-authoritative-reconstruction`
   - Title: `Reconcile verified AWS implementation, layout fixes, and test suites`
3. Review the complete diff via GitHub web interface.
4. Merge using standard "Squash and merge" or "Create a merge commit".

---

## 3. Rollback Plan (If Reversion is Ever Required)

If any unforeseen regression occurs post-merge:
```bash
# Revert the merge commit cleanly on main
git checkout main
git revert -m 1 <MERGE_COMMIT_HASH>
git push origin main
```

---

## 4. Aligning Production AWS Post-Merge (Future Operational Procedure)

> [!WARNING]
> **DO NOT EXECUTE AS PART OF PULL REQUEST REVIEW OR MERGE.**
> The commands below represent a future operational procedure that requires a separate, explicit deployment authorization and must not be run while reviewing or merging this pull request. Production updates should only occur after this pull request is merged into `main` and a dedicated maintenance window is scheduled.

### Future Operational Command Sequence (Requires Separate Deployment Approval)

When production deployment is independently approved and scheduled:
1. Connect via AWS Systems Manager session to the production EC2 host.
2. In `/opt/uehis`:
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```
3. Rebuild and restart the frontend container:
   ```bash
   sudo docker compose build frontend
   sudo docker compose up -d frontend
   ```
4. Verify that Nginx routes to the updated frontend container serving the verified 4-tier risk legend and positive scoring polarity.
