param([string]$Only = '')
$ErrorActionPreference = 'Stop'
$runRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $runRoot '../../../..')).Path
$sampleRoot = Join-Path $repoRoot 'specs/weekly-plan-authoring/validation/wp-a-simsun-20260909/samples'
$word = $null
$doc = $null
$results = @()
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $true
    # Keep alerts enabled. A successful COM call is NOT a visual warning check.
    $word.DisplayAlerts = -1
    $environment = [ordered]@{
        measured_at = (Get-Date -Format o)
        word_name = $word.Name
        word_version = $word.Version
        word_build = $word.Build
        active_printer = $word.ActivePrinter
        os = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture)
        culture = (Get-Culture).Name
        system_locale = (Get-WinSystemLocale).Name
        office = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration' | Select-Object VersionToReport,Platform,ProductReleaseIds)
        default_printer = @(Get-CimInstance Win32_Printer | Where-Object Default | Select-Object Name,DriverName)
        default_paper = (Get-PrintConfiguration -PrinterName 'Brother DCP-T725DW Printer' | Select-Object PaperSize,DuplexingMode,Color)
        native_observation = 'BLOCKED: Computer Use native pipe os error 2; initial/retry/reset-retry all failed'
        warning_observation = 'NOT OBSERVED; alerts enabled, OpenAndRepair false'
    }
    $environment | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $runRoot 'environment.json') -Encoding utf8
    $files = Get-ChildItem -LiteralPath $sampleRoot -Filter '*.docx' | Sort-Object Name
    if ($Only) { $files = $files | Where-Object BaseName -eq $Only }
    foreach ($inputFile in $files) {
        $outputDir = Join-Path $runRoot $inputFile.BaseName
        New-Item -ItemType Directory -Path $outputDir -ErrorAction Stop | Out-Null
        $before = (Get-FileHash -LiteralPath $inputFile.FullName).Hash.ToLowerInvariant()
        $entry = [ordered]@{sample=$inputFile.Name; started_at=(Get-Date -Format o); input_sha256=$before}
        try {
            $missing = [Type]::Missing
            # FileName, ConfirmConversions, ReadOnly, AddToRecentFiles; no repair.
            $doc = $word.Documents.Open($inputFile.FullName, $false, $true, $false, $missing, $missing, $false, $missing, $missing, $missing, $missing, $true, $false)
            $doc.Repaginate()
            $entry.word_pages = $doc.ComputeStatistics(2)
            $entry.compatibility_mode = $doc.CompatibilityMode
            $entry.read_only = $doc.ReadOnly
            $entry.zoom_percent = $doc.ActiveWindow.View.Zoom.Percentage
            $entry.view_type = $doc.ActiveWindow.View.Type
            $setup = $doc.Sections.Item(1).PageSetup
            $entry.geometry_points = [ordered]@{width=$setup.PageWidth;height=$setup.PageHeight;left=$setup.LeftMargin;right=$setup.RightMargin;top=$setup.TopMargin;bottom=$setup.BottomMargin;orientation=$setup.Orientation;paper_size=$setup.PaperSize}
            $entry.tables = $doc.Tables.Count
            $entry.rows = $doc.Tables.Item(1).Rows.Count
            $entry.requested_body_font = $doc.Tables.Item(1).Range.Font.NameFarEast
            $entry.body_size_pt = $doc.Tables.Item(1).Range.Font.Size
            $entry.body_line_spacing_pt = $doc.Tables.Item(1).Range.ParagraphFormat.LineSpacing
            $entry.body_line_spacing_rule = $doc.Tables.Item(1).Range.ParagraphFormat.LineSpacingRule
            $pdfPath = Join-Path $outputDir ($inputFile.BaseName + '.pdf')
            # 17 = PDF, 0 = print quality, 0 = all document, no properties or IRM.
            $doc.ExportAsFixedFormat($pdfPath, 17, $false, 0, 0, 1, 1, 0, $false, $false, 0, $true, $true, $false)
            $entry.pdf_sha256 = (Get-FileHash -LiteralPath $pdfPath).Hash.ToLowerInvariant()
            $entry.com_export = 'SUCCESS; native warning/preview observation still missing'
        } catch {
            $entry.com_export = 'BLOCKED'
            $entry.error = $_.Exception.Message
        } finally {
            if ($null -ne $doc) { $doc.Close(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc); $doc = $null }
            $entry.input_sha256_after = (Get-FileHash -LiteralPath $inputFile.FullName).Hash.ToLowerInvariant()
            $entry.finished_at = (Get-Date -Format o)
            $entry | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outputDir 'word.json') -Encoding utf8
            $results += $entry
            Write-Output ($entry | ConvertTo-Json -Compress -Depth 6)
        }
        if ($entry.input_sha256_after -ne $before) { throw 'INPUT HASH CHANGED: STOP' }
    }
} finally {
    $results | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $runRoot 'word-results.json') -Encoding utf8
    if ($null -ne $word) { $word.Quit(0); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }
}
