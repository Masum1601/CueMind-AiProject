# Autoplay + loop every video, add smooth fade transitions, export PNGs for QA
param([string]$Deck, [string]$PngDir)
$full = @(8, 9, 10)        # full gameplay videos: autoplay once
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open($Deck, $false, $false, $false)
$count = 0
foreach ($s in $p.Slides) {
    $s.SlideShowTransition.EntryEffect = 3849      # ppEffectFadeSmoothly
    $s.SlideShowTransition.Duration = 0.6
    foreach ($sh in $s.Shapes) {
        if ($sh.Type -eq 16) {
            $ps = $sh.AnimationSettings.PlaySettings
            $ps.PlayOnEntry = -1
            $ps.HideWhileNotPlaying = 0
            $ps.PauseAnimation = 0
            if ($full -contains $s.SlideIndex) { $ps.LoopUntilStopped = 0 } else { $ps.LoopUntilStopped = -1 }
            try { $sh.MediaFormat.Muted = $true } catch {}
            $count++
        }
    }
}
$p.Save()
if ($PngDir) {
    if (Test-Path $PngDir) { Remove-Item $PngDir -Recurse -Force }
    $p.SaveCopyAs($PngDir, 18)
}
$n = $p.Slides.Count
$p.Close()
$pp.Quit()
"slides $n, videos set to autoplay: $count"
