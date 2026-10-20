try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject("PowerPoint.Application")
    Write-Host "Presentations count:" $ppt.Presentations.Count
    for ($i = 1; $i -le $ppt.Presentations.Count; $i++) {
        Write-Host "Open presentation:" $ppt.Presentations.Item($i).FullName
    }
} catch {
    Write-Host "Error accessing PowerPoint:" $_
}
