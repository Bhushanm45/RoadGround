$pptxPath = 'C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI\RoadGuard_AI_Hardware_Hackathon_Idea.pptx'
$pdfPath = 'C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI\RoadGuard_AI_Hardware_Hackathon_Idea.pdf'
$pngDir = 'C:\Users\aryan\.gemini\antigravity\scratch\RoadGuard-AI\generated_slides'

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
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pptApp) | Out-Null
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()

Write-Host "Copying updated deliverables to Downloads..."
Copy-Item $pptxPath "C:\Users\aryan\Downloads\RoadGuard_AI_Hardware_Hackathon_Idea.pptx" -Force
Copy-Item $pdfPath "C:\Users\aryan\Downloads\RoadGuard_AI_Hardware_Hackathon_Idea.pdf" -Force

# Also copy slide PNGs to brain artifacts directory
$brainDir = "C:\Users\aryan\.gemini\antigravity\brain\0c03362b-d615-4f91-8096-b1c9b36d96de\slides"
New-Item -ItemType Directory -Force -Path $brainDir | Out-Null
Copy-Item (Join-Path $pngDir "*.png") $brainDir -Force

Write-Host "All exports and copies completed successfully!"
