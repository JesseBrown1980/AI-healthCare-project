# PowerShell script to delete old remote branches
# Review the branches before running this script

Write-Host "This script will delete the following remote branches:" -ForegroundColor Yellow
Write-Host ""

$branchesToDelete = @(
    "codex/add-multi-patient-dashboard-feature",
    "codex/add-push-notifications-after-analyses",
    "codex/add-service-container-and-app.state-wiring",
    "codex/add-unit-tests-for-epic-and-cerner-integration",
    "codex/extend-fhirconnector-for-epic-and-cerner",
    "codex/fix-fhir-connector-proxy-dependencies",
    "codex/improve-fhirconnector-error-handling-and-tests",
    "codex/integrate-fastapi-security-dependencies",
    "codex/remove-duplicate-tests-in-test_s_lora.py",
    "codex/resolve-merge-conflict-and-fix-push-notification-logic",
    "codex/update-ci-workflow-to-install-packages",
    "ci/add-ci-precommit",
    "2026-01-02-705q"
)

foreach ($branch in $branchesToDelete) {
    Write-Host "  - origin/$branch" -ForegroundColor Cyan
}

Write-Host ""
$confirm = Read-Host "Do you want to delete these branches? (yes/no)"

if ($confirm -eq "yes") {
    foreach ($branch in $branchesToDelete) {
        Write-Host "Deleting origin/$branch..." -ForegroundColor Yellow
        git push origin --delete $branch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Deleted origin/$branch" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed to delete origin/$branch (may not exist)" -ForegroundColor Red
        }
    }
    Write-Host ""
    Write-Host "Branch cleanup complete!" -ForegroundColor Green
} else {
    Write-Host "Branch deletion cancelled." -ForegroundColor Yellow
}
