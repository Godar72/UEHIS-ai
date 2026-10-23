# UEHIS — Recovery, Pull Request, and Rollback Plan

**Branch Name:** `recovery/aws-authoritative-reconstruction`  
**Base Target:** `origin/main`  
**Repository:** `https://github.com/Godar72/UEHIS-ai.git`  

---

## 1. Zero Production Mutation Confirmation

In accordance with strict safety mandates:
- **No changes have been pushed to GitHub `main`**.
- **No containers on AWS were stopped, restarted, or rebuilt**.
- **No production databases, Nginx routes, or DNS records were modified**.
- **The original workspace `C:\Users\adity\Desktop\SL` is 100% intact**.

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

## 4. Aligning Production AWS Post-Merge (Future Independent Step)

Once the recovery branch is approved and merged into `main`:
1. Connect via AWS Systems Manager session to the EC2 host.
2. In `/opt/uehis`:
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```
3. Rebuild the frontend container to replace the dormant test containers:
   ```bash
   sudo docker compose build frontend
   sudo docker compose up -d frontend
   ```
4. Verify Nginx routes to `uehis-frontend:latest` serving the verified 4-tier risk legend and positive scoring polarity.
