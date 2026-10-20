$pptxPath = 'C:\Users\aryan\Downloads\RoadGuard_AI_Fonts_Enlarged.pptx'
$pdfPath = 'C:\Users\aryan\Downloads\RoadGuard_AI_Fonts_Enlarged.pdf'
$pngDir = 'C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI\enlarged_slides'

Write-Host "Starting PowerPoint COM automation..."
$pptApp = New-Object -ComObject PowerPoint.Application
$pres = $pptApp.Presentations.Open($pptxPath, [Microsoft.Office.Core.MsoTriState]::msoTrue, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse)

Write-Host "Exporting PDF..."
$pres.SaveAs($pdfPath, 32)

Write-Host "Exporting PNG slides..."
New-Item -ItemType Directory -Force -Path $pngDir | Out-Null
for ($i = 1; $i -le $pres.Slides.Count; $i++) {
    $slidePng = Join-Path $pngDir ("slide_" + $i + ".png")
    $pres.Slides.Item($i).Export($slidePng, "PNG", 1920, 1080)
}

$pres.Close()
$pptApp.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pptApp) | Out-Null
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()

Write-Host "All exports completed successfully!"
