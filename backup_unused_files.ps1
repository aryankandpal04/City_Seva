$files = Get-Content -Path "backup_files_list.txt" | Where-Object { $_ -notmatch "^#" -and $_ -match "\S" }

foreach ($file in $files) {
    $file = $file.Trim()
    if (Test-Path $file) {
        Write-Host "Moving $file to backup_unused/"
        Move-Item -Path $file -Destination "backup_unused/" -Force
    } else {
        Write-Host "File not found: $file"
    }
}

Write-Host "Backup complete. All duplicate and unused files have been moved to backup_unused/" 