<#
.SYNOPSIS
Installs the Education Analytics data platform into a Microsoft Fabric workspace.

.DESCRIPTION
Run without arguments for the guided wizard. For CI/CD, provide -WorkspaceName and the
desired switches. The installer is safe to rerun: it reuses Lakehouses, updates managed
artifacts, preserves EDU_Config unless explicitly replaced, and validates jobs to a terminal
state. Use -PlanOnly to validate all local inputs and generated definitions without changing
Fabric.

.EXAMPLE
./Install-IntoWorkspace.ps1

Starts the interactive wizard.

.EXAMPLE
./Install-IntoWorkspace.ps1 -WorkspaceName "EDUCATION-ANALYTICS" -PlanOnly

Validates the complete package without changing Fabric.

.EXAMPLE
./Install-IntoWorkspace.ps1 -WorkspaceName "EDUCATION-ANALYTICS" `
    -RunNotebook -RunSilverCreateSchemaNotebook -RunSilverTransformNotebook

Uploads the Bronze package and runs Bronze-to-Silver in dependency order.

.EXAMPLE
./Install-IntoWorkspace.ps1 -WorkspaceName "EDUCATION-ANALYTICS" `
    -PeriodStart "2024-09-01" -PeriodEnd "2026-05-09" `
    -RunEndToEndPipeline -OverwriteSharedConfigNotebook

Deploys all artifacts and runs the Bronze-to-Gold pipeline for a half-open reporting period.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$WorkspaceName,

    [Parameter(Mandatory = $false)]
    [string]$SolutionName,

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]*$')]
    [string]$Prefix = 'EDU_',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$SemanticModelBaseName = 'Analytics',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$ReportBaseName = 'Insights',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$LakehouseBaseName = 'Bronze',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$BronzeSchemaNotebookBaseName = 'BR_CreateSchema',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$NotebookBaseName = 'BR_Ingestion',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$SilverLakehouseBaseName = 'SL',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$SilverNotebookBaseName = 'SL_CreateSchema',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$TransformNotebookBaseName = 'BR_SL_Transform',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$GoldLakehouseBaseName = 'GD',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$ConfigNotebookBaseName = 'Config',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$GoldNotebookBaseName = 'GD_CreateSchema',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$EnrichmentNotebookBaseName = 'SL_GD_Enrichment',

    [Parameter(Mandatory = $false)]
    [Alias('EnrichmentPipelineBaseName')]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$ProcessingPipelineBaseName = 'BR_GD_Processing',

    [Parameter(Mandatory = $false)]
    [string]$PeriodStart,

    [Parameter(Mandatory = $false)]
    [string]$PeriodEnd,

    [Parameter(Mandatory = $false)]
    [Alias('RunBronzeIngestionNotebook')]
    [switch]$RunNotebook,

    [Parameter(Mandatory = $false)]
    [switch]$RunSilverCreateSchemaNotebook,

    [Parameter(Mandatory = $false)]
    [switch]$RunSilverTransformNotebook,

    [Parameter(Mandatory = $false)]
    [switch]$RunGoldCreateSchemaNotebook,

    [Parameter(Mandatory = $false)]
    [Alias('RunSilverToGoldEnrichmentPipeline')]
    [switch]$RunEndToEndPipeline,

    [Parameter(Mandatory = $false)]
    [switch]$OverwriteSharedConfigNotebook,

    [Parameter(Mandatory = $false)]
    [switch]$SkipLocalValidation,

    [Parameter(Mandatory = $false)]
    [switch]$SkipBronzeDataUpload,

    [Parameter(Mandatory = $false)]
    [switch]$RemoveRetiredPipeline,

    [Parameter(Mandatory = $false)]
    [switch]$PlanOnly,

    [Parameter(Mandatory = $false)]
    [switch]$Interactive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The Fabric CLI writes Unicode status glyphs. Without UTF-8 its output fails on the
# default Windows code page, which surfaces as an unrelated "charmap codec" error.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

function Write-InstallerBanner {
    Write-Host ''
    Write-Host '+------------------------------------------------------------+' -ForegroundColor DarkCyan
    Write-Host '|    EDUCATION ANALYTICS    |  MICROSOFT FABRIC INSTALLER   |' -ForegroundColor Cyan
    Write-Host '+------------------------------------------------------------+' -ForegroundColor DarkCyan
    Write-Host ''
}

function Write-InstallerSection {
    param([Parameter(Mandatory = $true)][string]$Title)

    Write-Host ''
    Write-Host "-- $Title " -ForegroundColor Cyan -NoNewline
    Write-Host ('-' * [Math]::Max(1, 56 - $Title.Length)) -ForegroundColor DarkCyan
}

function Write-InstallerStatus {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('Info', 'Success', 'Warning')][string]$Type,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $style = switch ($Type) {
        'Success' { @{ Label = '[OK]'; Color = 'Green' } }
        'Warning' { @{ Label = '[!]'; Color = 'Yellow' } }
        default { @{ Label = '[>]'; Color = 'Gray' } }
    }
    Write-Host $style.Label -ForegroundColor $style.Color -NoNewline
    Write-Host " $Message"
}

function Read-InstallerValue {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $false)][string]$Default
    )

    $label = if ($Default) { "$Prompt [$Default]" } else { $Prompt }
    $value = Read-Host $label
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value.Trim()
}

function Read-InstallerChoice {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string[]]$Allowed,
        [Parameter(Mandatory = $true)][string]$Default
    )

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $choice = Read-InstallerValue -Prompt $Prompt -Default $Default
        if ($choice -in $Allowed) { return $choice }
        Write-InstallerStatus -Type Warning -Message "Choose one of: $($Allowed -join ', ')."
    }
    throw "No valid choice was supplied for: $Prompt"
}

function Test-InstallerConfirmation {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $false)][bool]$Default = $false
    )

    $defaultLabel = if ($Default) { 'Y/n' } else { 'y/N' }
    $rawAnswer = Read-Host "$Prompt [$defaultLabel]"
    if ($null -eq $rawAnswer) { return $false }
    $answer = $rawAnswer.Trim().ToLowerInvariant()
    if (-not $answer) { return $Default }
    return $answer -in @('y', 'yes')
}

function Write-InstallerPlan {
    $workflow = if ($PlanOnly) {
        'Preview only'
    }
    elseif ($RunEndToEndPipeline) {
        'Full Bronze -> Silver -> Gold pipeline'
    }
    elseif ($RunSilverTransformNotebook) {
        'Bronze -> Silver pipeline'
    }
    elseif ($RunNotebook -or $RunSilverCreateSchemaNotebook -or $RunGoldCreateSchemaNotebook) {
        'Custom deployment and execution'
    }
    else {
        'Deploy artifacts only'
    }

    Write-InstallerSection -Title 'Deployment plan'
    $rows = @(
        @{ Label = 'Workspace'; Value = $WorkspaceName }
        @{ Label = 'Solution folder'; Value = $(if ($solutionFolderName) { $solutionFolderName } else { 'Workspace root (legacy mode)' }) }
        @{ Label = 'Artifact prefix'; Value = $Prefix }
        @{ Label = 'Workflow'; Value = $workflow }
        @{ Label = 'Artifacts'; Value = '3 Lakehouses, 7 notebooks, 1 pipeline, 1 semantic model, 1 report' }
        @{ Label = 'Bronze files'; Value = $(if ($PlanOnly) { 'Validate only' } elseif ($SkipBronzeDataUpload) { 'Keep existing' } else { 'Upload 28 CSV files + manifest' }) }
        @{ Label = 'Retired pipeline'; Value = $(if ($RemoveRetiredPipeline) { 'Remove if present' } else { 'Keep if present' }) }
        @{ Label = 'Reporting period'; Value = $(if ($PeriodStart) { "[$PeriodStart, $PeriodEnd)" } else { 'Not configured' }) }
        @{ Label = 'Shared config'; Value = $(if ($OverwriteSharedConfigNotebook) { 'Replace if present' } else { 'Preserve if present' }) }
    )
    foreach ($row in $rows) {
        Write-Host ('  {0,-18} {1}' -f ($row.Label + ':'), $row.Value)
    }
}

function Write-InstallerSummary {
    Write-InstallerSection -Title 'Installation complete'
    $resources = @(
        @{ Label = 'Bronze Lakehouse'; Value = $lakehousePath }
        @{ Label = 'Silver Lakehouse'; Value = $silverLakehousePath }
        @{ Label = 'Gold Lakehouse'; Value = $goldLakehousePath }
        @{ Label = 'Bronze schema'; Value = $bronzeSchemaNotebookFabricPath }
        @{ Label = 'Bronze notebook'; Value = $notebookFabricPath }
        @{ Label = 'Silver schema'; Value = $silverNotebookFabricPath }
        @{ Label = 'Silver transform'; Value = $transformNotebookFabricPath }
        @{ Label = 'Shared config'; Value = $configNotebookFabricPath }
        @{ Label = 'Gold schema'; Value = $goldNotebookFabricPath }
        @{ Label = 'Gold enrichment'; Value = $enrichmentNotebookFabricPath }
        @{ Label = 'Processing pipeline'; Value = $processingPipelineFabricPath }
        @{ Label = 'Semantic model'; Value = $semanticModelFabricPath }
        @{ Label = 'Power BI report'; Value = $reportFabricPath }
    )
    foreach ($resource in $resources) {
        Write-Host ('  {0,-18} {1}' -f ($resource.Label + ':'), $resource.Value)
    }

    Write-Host ''
    Write-InstallerStatus -Type Success -Message "Uploaded files: $(if ($SkipBronzeDataUpload) { 0 } else { $csvFiles.Count + 1 })"
    foreach ($run in @(
        @{ Name = 'End-to-end pipeline'; Requested = [bool]$RunEndToEndPipeline }
        @{ Name = 'Bronze ingestion'; Requested = [bool]($RunNotebook -and -not $RunEndToEndPipeline) }
        @{ Name = 'Silver schema'; Requested = [bool]($RunSilverCreateSchemaNotebook -and -not $RunEndToEndPipeline) }
        @{ Name = 'Silver transform'; Requested = [bool]($RunSilverTransformNotebook -and -not $RunEndToEndPipeline) }
        @{ Name = 'Gold schema'; Requested = [bool]($RunGoldCreateSchemaNotebook -and -not $RunEndToEndPipeline) }
        @{ Name = 'Semantic model refresh'; Requested = [bool]$script:semanticModelRefreshed }
    )) {
        $state = if ($run.Requested) { 'completed' } else { 'not requested' }
        Write-InstallerStatus -Type $(if ($run.Requested) { 'Success' } else { 'Info' }) -Message "$($run.Name): $state"
    }
}

function Invoke-InteractiveSetup {
    Write-InstallerBanner
    Write-Host 'A guided setup for previewing, deploying, or running the complete data pipeline.' -ForegroundColor Gray

    for ($attempt = 1; [string]::IsNullOrWhiteSpace($script:WorkspaceName) -and $attempt -le 3; $attempt++) {
        $script:WorkspaceName = Read-InstallerValue -Prompt 'Fabric workspace name'
        if ([string]::IsNullOrWhiteSpace($script:WorkspaceName)) {
            Write-InstallerStatus -Type Warning -Message 'Workspace name is required.'
        }
    }
    if ([string]::IsNullOrWhiteSpace($script:WorkspaceName)) {
        throw 'Workspace name was not supplied.'
    }

    Write-InstallerSection -Title 'Choose a workflow'
    Write-Host '  1  Preview only          Validate everything; change nothing' -ForegroundColor Gray
    Write-Host '  2  Deploy artifacts      Create/update Fabric items; run nothing' -ForegroundColor Gray
    Write-Host '  3  Build Bronze + Silver Upload source data and populate Silver' -ForegroundColor Gray
    Write-Host '  4  Run full pipeline     Bronze -> Silver -> Gold' -ForegroundColor Gray
    $workflow = Read-InstallerChoice -Prompt 'Workflow' -Allowed @('1', '2', '3', '4') -Default '1'

    switch ($workflow) {
        '1' { $script:PlanOnly = $true }
        '3' {
            $script:RunNotebook = $true
            $script:RunSilverCreateSchemaNotebook = $true
            $script:RunSilverTransformNotebook = $true
        }
        '4' {
            $script:RunEndToEndPipeline = $true
            $script:PeriodStart = Read-InstallerValue -Prompt 'Reporting period start (YYYY-MM-DD)' -Default '2024-09-01'
            $script:PeriodEnd = Read-InstallerValue -Prompt 'Reporting period end, exclusive (YYYY-MM-DD)' -Default '2026-05-09'
        }
    }

    if (-not $script:PlanOnly) {
        $uploadBronze = Test-InstallerConfirmation -Prompt 'Upload or refresh Bronze sample files?' -Default $true
        $script:SkipBronzeDataUpload = -not $uploadBronze
        $script:RemoveRetiredPipeline = Test-InstallerConfirmation `
            -Prompt "Remove retired ${Prefix}SL_GD_Enrichment pipeline if present?" `
            -Default $false
        $script:OverwriteSharedConfigNotebook = Test-InstallerConfirmation `
            -Prompt 'Replace an existing shared EDU_Config notebook?' `
            -Default ([bool]$script:RunEndToEndPipeline)
    }
}

$nonInteractiveHost = [bool]$env:CI -or [Console]::IsInputRedirected
if ([string]::IsNullOrWhiteSpace($WorkspaceName) -and -not $Interactive -and $nonInteractiveHost) {
    throw '-WorkspaceName is required in non-interactive sessions. Use -Interactive to force the guided wizard.'
}
$script:interactiveSession = $Interactive -or [string]::IsNullOrWhiteSpace($WorkspaceName)
if ($script:interactiveSession) {
    Invoke-InteractiveSetup
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$sampleDataPath = Join-Path $repositoryRoot 'sample-data'
$manifestPath = Join-Path $sampleDataPath 'manifest.json'
$bronzeSchemaNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_BR_CreateSchema.ipynb'
$notebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_BR_Ingestion.ipynb'
$silverNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_SL_CreateSchema.ipynb'
$transformNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_BR_SL_Transform.ipynb'
$configNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_Config.ipynb'
$goldNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_GD_CreateSchema.ipynb'
$enrichmentNotebookPath = Join-Path $repositoryRoot 'src/fabric/notebooks/EDU_SL_GD_Enrichment.ipynb'
$processingPipelinePath = Join-Path $repositoryRoot 'src/fabric/pipelines/EDU_BR_GD_Processing.DataPipeline/pipeline-content.json'
$semanticModelSourcePath = Join-Path $repositoryRoot 'src/power-bi/EducationAnalytics.SemanticModel'
$reportSourcePath = Join-Path $repositoryRoot 'src/power-bi/EducationAnalytics.Report'
$sourceFolders = @('PowerSchool', 'Canvas', 'Moodle', 'NWEA')
$landingPath = 'landing/education-analytics'
$solutionFolderName = $null
if ($SolutionName) {
    $solutionFolderName = (($SolutionName -replace '[\x00-\x1F\x7F-\x9F~"#.&*:<>?/\\{|}]', '_') -replace '\s+', ' ').Trim()
    $instancePrefix = (($SolutionName.Normalize([Text.NormalizationForm]::FormKD) -replace '[^A-Za-z0-9_]+', '_') -replace '_+', '_').Trim('_')
    if (-not $solutionFolderName -or $solutionFolderName.ToLowerInvariant() -in @('$recycle.bin', 'recycled', 'recycler')) {
        throw 'SolutionName cannot be converted to a valid Fabric folder name.'
    }
    if (-not $instancePrefix) { throw 'SolutionName cannot be converted to a valid artifact prefix.' }
    if ($solutionFolderName.Length -gt 255) { $solutionFolderName = $solutionFolderName.Substring(0, 255) }
    if ($instancePrefix.Length -gt 80) { $instancePrefix = $instancePrefix.Substring(0, 80) }
    $Prefix = "${instancePrefix}_"
}
$lakehouseName = "${Prefix}${LakehouseBaseName}"
$bronzeSchemaNotebookName = "${Prefix}${BronzeSchemaNotebookBaseName}"
$notebookName = "${Prefix}${NotebookBaseName}"
$silverLakehouseName = "${Prefix}${SilverLakehouseBaseName}"
$silverNotebookName = "${Prefix}${SilverNotebookBaseName}"
$transformNotebookName = "${Prefix}${TransformNotebookBaseName}"
$goldLakehouseName = "${Prefix}${GoldLakehouseBaseName}"
$configNotebookName = "${Prefix}${ConfigNotebookBaseName}"
$goldNotebookName = "${Prefix}${GoldNotebookBaseName}"
$enrichmentNotebookName = "${Prefix}${EnrichmentNotebookBaseName}"
$processingPipelineName = "${Prefix}${ProcessingPipelineBaseName}"
$semanticModelName = "${Prefix}${SemanticModelBaseName}"
$reportName = "${Prefix}${ReportBaseName}"
$workspacePath = "${WorkspaceName}.Workspace"
$artifactRootPath = if ($solutionFolderName) { "$workspacePath/$solutionFolderName" } else { $workspacePath }
$lakehousePath = "$artifactRootPath/${lakehouseName}.Lakehouse"
$bronzeSchemaNotebookFabricPath = "$artifactRootPath/${bronzeSchemaNotebookName}.Notebook"
$notebookFabricPath = "$artifactRootPath/${notebookName}.Notebook"
$silverLakehousePath = "$artifactRootPath/${silverLakehouseName}.Lakehouse"
$silverNotebookFabricPath = "$artifactRootPath/${silverNotebookName}.Notebook"
$transformNotebookFabricPath = "$artifactRootPath/${transformNotebookName}.Notebook"
$goldLakehousePath = "$artifactRootPath/${goldLakehouseName}.Lakehouse"
$configNotebookFabricPath = "$artifactRootPath/${configNotebookName}.Notebook"
$goldNotebookFabricPath = "$artifactRootPath/${goldNotebookName}.Notebook"
$enrichmentNotebookFabricPath = "$artifactRootPath/${enrichmentNotebookName}.Notebook"
$processingPipelineFabricPath = "$artifactRootPath/${processingPipelineName}.DataPipeline"
$semanticModelFabricPath = "$artifactRootPath/${semanticModelName}.SemanticModel"
$reportFabricPath = "$artifactRootPath/${reportName}.Report"
$legacyEnrichmentPipelineFabricPath = "$artifactRootPath/${Prefix}SL_GD_Enrichment.DataPipeline"

if ($goldLakehouseName -in @($lakehouseName, $silverLakehouseName)) {
    throw 'The Gold Lakehouse name must differ from the Bronze and Silver Lakehouse names.'
}
if ([bool]$PeriodStart -ne [bool]$PeriodEnd) {
    throw 'Specify both -PeriodStart and -PeriodEnd, or neither.'
}
$parsedPeriod = @(@($PeriodStart, $PeriodEnd) | Where-Object { $_ } | ForEach-Object {
    $parsed = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($_, 'yyyy-MM-dd', [cultureinfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::None, [ref]$parsed)) {
        throw "Reporting period dates must use YYYY-MM-DD: $_"
    }
    $parsed
})
if ($parsedPeriod.Count -eq 2 -and $parsedPeriod[0] -ge $parsedPeriod[1]) {
    throw 'PeriodEnd must be later than PeriodStart; the end date is exclusive.'
}
if ($RunEndToEndPipeline -and -not $PeriodStart) {
    throw '-RunEndToEndPipeline requires -PeriodStart and -PeriodEnd.'
}

# Reporting period already configured in the deployed notebook, resolved later against the
# live workspace. Declared here so placeholder substitution can read it under StrictMode.
$script:effectivePeriod = $null

# Whether the deployed semantic model was refreshed. Declared for StrictMode because the
# summary reads it even on runs that stop before the reporting section sets it.
$script:semanticModelRefreshed = $false

function Invoke-FabricCli {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $false)]
        [switch]$ReturnOutput
    )

    Write-Verbose "fab $($Arguments -join ' ')"
    $output = & fab @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Fabric CLI command failed: fab $($Arguments -join ' ')`n$($output -join [Environment]::NewLine)"
    }

    if ($ReturnOutput) {
        return ($output -join [Environment]::NewLine).Trim()
    }
}

function Invoke-PowerBiApi {
    <#
        Call a Power BI REST endpoint through the Fabric CLI.

        Gateway binding and dataset refresh have no Fabric REST equivalent, but the CLI
        already holds a token for the Power BI audience. Routing through `-A powerbi`
        keeps the installer on the single `fab auth login` identity, so no second sign-in
        and no separate Azure CLI installation is required.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Endpoint,

        [Parameter(Mandatory = $false)]
        [ValidateSet('get', 'post', 'patch', 'put', 'delete')]
        [string]$Method = 'get',

        [Parameter(Mandatory = $false)]
        [string]$Body,

        [Parameter(Mandatory = $false)]
        [string]$Params,

        [Parameter(Mandatory = $false)]
        [switch]$ShowHeaders
    )

    $arguments = @('api', $Endpoint, '-A', 'powerbi', '-X', $Method)
    if ($Params) { $arguments += @('-P', $Params) }
    if ($ShowHeaders) { $arguments += '--show_headers' }

    $bodyFile = $null
    try {
        if ($PSBoundParameters.ContainsKey('Body') -and $Body) {
            $bodyFile = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-body-" + [guid]::NewGuid() + '.json')
            [System.IO.File]::WriteAllText($bodyFile, $Body, [System.Text.UTF8Encoding]::new($false))
            $arguments += @('-i', $bodyFile)
        }
        $raw = Invoke-FabricCli -Arguments $arguments -ReturnOutput
    }
    finally {
        if ($bodyFile) { Remove-Item -LiteralPath $bodyFile -Force -ErrorAction SilentlyContinue }
    }

    if (-not $raw) { return $null }
    $response = $raw | ConvertFrom-Json
    # The CLI reports transport success even when the service rejects the request.
    if ($response.PSObject.Properties['status_code'] -and [int]$response.status_code -ge 400) {
        throw "Power BI API call failed with status $($response.status_code): $Endpoint`n$($response.text | ConvertTo-Json -Depth 10 -Compress)"
    }
    return $response
}

function Test-FabricPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $output = & fab exists $Path 2>&1
    if ($LASTEXITCODE -ne 0) {
        return $false
    }

    $result = ($output -join [Environment]::NewLine).Trim()
    return $result -match '(?im)(?:^|\s)true\s*$'
}

function Get-FabricProperty {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Property
    )

    $value = Invoke-FabricCli -Arguments @('get', $Path, '-q', $Property) -ReturnOutput
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        return $value.Trim('"')
    }
    return $value
}

function Get-OptionalProperty {
    <#
        Read a property that the service may legitimately omit.

        StrictMode turns any missing-property access into a terminating error, so optional
        fields in Fabric and Power BI responses have to be probed rather than dereferenced.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $InputObject,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if ($null -eq $InputObject -or $InputObject -is [string]) { return $null }
    if (-not $InputObject.PSObject.Properties[$Name]) { return $null }
    return $InputObject.$Name
}

function Set-JsonProperty {    param(
        [Parameter(Mandatory = $true)]
        [psobject]$InputObject,

        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $false)]
        $Value
    )

    if ($InputObject.PSObject.Properties[$Name]) {
        $InputObject.$Name = $Value
    }
    else {
        $InputObject | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Test-LocalArtifacts {
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Manifest not found: $manifestPath"
    }
    if (-not (Test-Path -LiteralPath $bronzeSchemaNotebookPath -PathType Leaf)) {
        throw "Bronze schema notebook not found: $bronzeSchemaNotebookPath"
    }
    if (-not (Test-Path -LiteralPath $notebookPath -PathType Leaf)) {
        throw "Notebook not found: $notebookPath"
    }
    if (-not (Test-Path -LiteralPath $silverNotebookPath -PathType Leaf)) {
        throw "Silver notebook not found: $silverNotebookPath"
    }
    if (-not (Test-Path -LiteralPath $transformNotebookPath -PathType Leaf)) {
        throw "Silver transform notebook not found: $transformNotebookPath"
    }
    foreach ($goldArtifact in @($configNotebookPath, $goldNotebookPath, $enrichmentNotebookPath, $processingPipelinePath)) {
        if (-not (Test-Path -LiteralPath $goldArtifact -PathType Leaf)) {
            throw "Gold artifact not found: $goldArtifact"
        }
    }

    $csvFiles = foreach ($sourceFolder in $sourceFolders) {
        $sourcePath = Join-Path $sampleDataPath $sourceFolder
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Container)) {
            throw "Source folder not found: $sourcePath"
        }
        Get-ChildItem -LiteralPath $sourcePath -File -Filter '*.csv' -Recurse
    }

    if (@($csvFiles).Count -ne 28) {
        throw "Expected 28 source CSV files, found $(@($csvFiles).Count)."
    }

    $null = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $null = Get-Content -LiteralPath $bronzeSchemaNotebookPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $null = Get-Content -LiteralPath $notebookPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $null = Get-Content -LiteralPath $silverNotebookPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $null = Get-Content -LiteralPath $transformNotebookPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($goldArtifact in @($configNotebookPath, $goldNotebookPath, $enrichmentNotebookPath, $processingPipelinePath)) {
        $null = Get-Content -LiteralPath $goldArtifact -Raw -Encoding UTF8 | ConvertFrom-Json
    }

    $pythonRequired = $PlanOnly -or -not $SkipLocalValidation
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonRequired -and -not $python) {
        throw 'Python 3.11+ is required to validate generated notebook code.'
    }
    $script:pythonPath = if ($python) { $python.Source } else { $null }

    if (-not $SkipLocalValidation) {
        $validationOutput = & $python.Source (Join-Path $sampleDataPath 'generate.py') --check
        if ($LASTEXITCODE -ne 0) {
            throw 'Sample-data validation failed.'
        }
        Write-Verbose ($validationOutput -join [Environment]::NewLine)
        Write-InstallerStatus -Type Success -Message 'Sample package validation passed.'
    }

    return @($csvFiles)
}

function Get-DeployedReportingPeriod {
    <#
        Read the reporting period already configured in the deployed enrichment notebook.

        Every install re-imports that notebook, so substituting the placeholders with
        nothing would quietly erase a working period and break a scheduled pipeline.
        The deployed values are treated as configuration to preserve, not to overwrite.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-FabricPath -Path $Path)) { return $null }

    try {
        $itemId = Get-FabricItemId -Path $Path -Attempts 3
        $response = (Invoke-FabricCli -Arguments @('api', "workspaces/$workspaceId/items/$itemId/getDefinition?format=ipynb", '-X', 'post', '--show_headers') -ReturnOutput) | ConvertFrom-Json
        $parts = $response.text.definition.parts
        if (-not $parts) {
            $location = [string]$response.headers.Location
            if ($location -notmatch '/operations/([0-9a-fA-F-]{36})') {
                throw 'Fabric returned neither a notebook definition nor an operation ID.'
            }

            $operationId = $Matches[1]
            $lastError = $null
            for ($attempt = 1; $attempt -le 10 -and -not $parts; $attempt++) {
                try {
                    $result = (Invoke-FabricCli -Arguments @('api', "operations/$operationId/result") -ReturnOutput) | ConvertFrom-Json
                    $parts = $result.text.definition.parts
                }
                catch {
                    $lastError = $_
                }
                if (-not $parts -and $attempt -lt 10) { Start-Sleep -Seconds ([Math]::Min($attempt * 2, 10)) }
            }
            if (-not $parts) {
                $detail = if ($lastError) { $lastError.Exception.Message } else { 'No result was returned.' }
                throw "Fabric operation $operationId did not return the notebook definition. $detail"
            }
        }
        $part = $parts | Where-Object { $_.path -match 'notebook-content' } | Select-Object -First 1
        if (-not $part) { throw 'The deployed notebook definition has no notebook-content part.' }

        $content = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($part.payload))
        $start = if ($content -match 'period_start\s*=\s*\\?"([0-9]{4}-[0-9]{2}-[0-9]{2})\\?"') { $Matches[1] } else { $null }
        $end = if ($content -match 'period_end\s*=\s*\\?"([0-9]{4}-[0-9]{2}-[0-9]{2})\\?"') { $Matches[1] } else { $null }
        if ($start -and $end) { return @{ Start = $start; End = $end } }
        if (-not $start -and -not $end -and
                $content.Contains('{PERIOD_START}') -and $content.Contains('{PERIOD_END}')) {
            return $null
        }
        throw 'The deployed notebook does not contain a valid reporting period.'
    }
    catch {
        throw "Could not preserve the deployed reporting period. Supply -PeriodStart and -PeriodEnd, or correct access to $Path. $($_.Exception.Message)"
    }
}

function Get-ConfigReplacements {
    <#
        Environment names stay out of the checked-in notebooks. The Silver and Gold
        Lakehouses use the default namespace, so the schema tokens resolve to empty and
        the notebooks fall back to two-part table names.

        The reporting period is only substituted when it was supplied. Installing Bronze or
        Silver alone must not require a Gold-specific parameter, so without it the tokens are
        left in place and the notebook's own guard refuses to run until they are set.
    #>
    $map = @{
        '{SILVER_LAKEHOUSE_NAME}' = $silverLakehouseName
        '{SILVER_SCHEMA_NAME}' = ''
        '{GOLD_LAKEHOUSE_NAME}' = $goldLakehouseName
        '{GOLD_SCHEMA_NAME}' = ''
        '%run <EDU_Config>' = "%run $configNotebookName"
    }
    # Explicit values win; otherwise keep whatever the deployed notebook already uses.
    if ($PeriodStart) {
        $map['{PERIOD_START}'] = $PeriodStart
        $map['{PERIOD_END}'] = $PeriodEnd
    }
    elseif ($script:effectivePeriod) {
        $map['{PERIOD_START}'] = $script:effectivePeriod.Start
        $map['{PERIOD_END}'] = $script:effectivePeriod.End
    }
    return $map
}

function New-PreparedNotebook {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,

        [Parameter(Mandatory = $true)]
        [string]$ItemName,

        [Parameter(Mandatory = $true)]
        [string]$WorkspaceId,

        [Parameter(Mandatory = $true)]
        [string]$LakehouseId,

        [Parameter(Mandatory = $true)]
        [string]$LakehouseName,

        [Parameter(Mandatory = $false)]
        [string[]]$AdditionalLakehouseIds = @(),

        [Parameter(Mandatory = $false)]
        [hashtable]$Replacements = @{},

        [Parameter(Mandatory = $false)]
        [hashtable]$ParameterValues = @{}
    )

    $temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-" + [guid]::NewGuid())
    $notebookDirectory = Join-Path $temporaryDirectory "${ItemName}.Notebook"
    $preparedNotebookPath = Join-Path $notebookDirectory 'notebook-content.ipynb'
    New-Item -ItemType Directory -Path $notebookDirectory -Force | Out-Null

    $notebook = Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $notebook.metadata) {
        Set-JsonProperty -InputObject $notebook -Name 'metadata' -Value ([pscustomobject]@{})
    }

    # The shared configuration notebook holds functions only, so it needs no Lakehouse.
    $known = @($LakehouseId) + @($AdditionalLakehouseIds) | Where-Object { $_ } | Select-Object -Unique
    $lakehouseDependency = [pscustomobject]@{
        default_lakehouse = $LakehouseId
        default_lakehouse_name = $LakehouseName
        default_lakehouse_workspace_id = $WorkspaceId
        known_lakehouses = @($known | ForEach-Object { [pscustomobject]@{ id = $_ } })
    }
    Set-JsonProperty -InputObject $notebook.metadata -Name 'dependencies' -Value ([pscustomobject]@{
        lakehouse = $lakehouseDependency
    })
    Set-JsonProperty -InputObject $notebook.metadata -Name 'kernel_info' -Value ([pscustomobject]@{
        name = 'synapse_pyspark'
    })
    Set-JsonProperty -InputObject $notebook.metadata -Name 'kernelspec' -Value ([pscustomobject]@{
        display_name = 'synapse_pyspark'
        name = 'synapse_pyspark'
    })
    Set-JsonProperty -InputObject $notebook.metadata -Name 'language_info' -Value ([pscustomobject]@{
        name = 'python'
    })
    Set-JsonProperty -InputObject $notebook.metadata -Name 'microsoft' -Value ([pscustomobject]@{
        language = 'python'
        language_group = 'synapse_pyspark'
    })

    # Placeholders keep environment names out of the checked-in definitions.
    if ($Replacements.Count) {
        foreach ($cell in $notebook.cells) {
            if ($cell.cell_type -ne 'code') { continue }
            $cell.source = @($cell.source | ForEach-Object {
                $line = $_
                foreach ($token in $Replacements.Keys) { $line = $line.Replace($token, [string]$Replacements[$token]) }
                $line
            })
        }
    }

    $parameterCell = $notebook.cells | Where-Object {
        $_.cell_type -eq 'code' -and ($_.source -join "`n") -match '^# Deployment parameters'
    } | Select-Object -First 1
    if ($parameterCell) {
        Set-JsonProperty -InputObject $parameterCell.metadata -Name 'tags' -Value @('parameters')
    }
    else {
        throw "Could not find the deployment parameters cell in $ItemName."
    }
    foreach ($parameterName in $ParameterValues.Keys) {
        $replacement = "$parameterName = $($ParameterValues[$parameterName])"
        $matched = $false
        $parameterCell.source = @($parameterCell.source | ForEach-Object {
            if ($_ -match "^$([regex]::Escape($parameterName))\s*=") {
                $matched = $true
                $replacement + "`n"
            }
            else {
                $_
            }
        })
        if (-not $matched) {
            throw "Parameter '$parameterName' was not found in notebook '$SourcePath'."
        }
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    $notebookJson = $notebook | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText($preparedNotebookPath, $notebookJson, $utf8NoBom)

    return [pscustomobject]@{
        Directory = $notebookDirectory
        Root = $temporaryDirectory
    }
}

function New-PreparedPipeline {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,

        [Parameter(Mandatory = $true)]
        [string]$ItemName,

        [Parameter(Mandatory = $true)]
        [hashtable]$Replacements
    )

    $temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-" + [guid]::NewGuid())
    $pipelineDirectory = Join-Path $temporaryDirectory "${ItemName}.DataPipeline"
    New-Item -ItemType Directory -Path $pipelineDirectory -Force | Out-Null

    $content = Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8
    foreach ($token in $Replacements.Keys) { $content = $content.Replace($token, [string]$Replacements[$token]) }
    $pipeline = $content | ConvertFrom-Json

    $activities = @($pipeline.properties.activities)
    if ($pipeline.properties.concurrency -ne 1 -or $activities.Count -ne 6) {
        throw 'The processing pipeline must declare concurrency 1 and exactly six activities.'
    }
    foreach ($activity in $activities) {
        if ($activity.typeProperties.notebookId -notmatch '^[0-9a-fA-F-]{36}$') {
            throw "Pipeline activity $($activity.name) has an unresolved notebook ID."
        }
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText((Join-Path $pipelineDirectory 'pipeline-content.json'),
        ($pipeline | ConvertTo-Json -Depth 100), $utf8NoBom)

    return [pscustomobject]@{
        Directory = $pipelineDirectory
        Root = $temporaryDirectory
    }
}

function Get-ModelConnectionString {
    <#
        Build the live-connect string that binds a report to a deployed semantic model.

        Fabric resolves the target by GUID, so the workspace and model names alone are not
        enough: the import fails with InvalidConnectionInformation unless `semanticModelId`
        carries the deployed model's ID.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$SemanticModelName,
        [Parameter(Mandatory = $true)][string]$SemanticModelId
    )

    return "Data Source=powerbi://api.powerbi.com/v1.0/myorg/$WorkspaceName;Initial Catalog=$SemanticModelName;semanticModelId=$SemanticModelId"
}

function New-PreparedReportingItems {
    <#
        Stage the semantic model and report for import.

        The checked-in PBIP binds the report to the model by relative path, which is what
        Power BI Desktop needs. The Fabric import API rejects `byPath`, so the staged report
        is rebound with the XMLA live-connect string for the deployed model. The 2.0.0
        report schema allows `connectionString` and nothing else inside `byConnection`.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$SemanticModelSourcePath,
        [Parameter(Mandatory = $true)][string]$ReportSourcePath,
        [Parameter(Mandatory = $true)][string]$SemanticModelName,
        [Parameter(Mandatory = $true)][string]$ReportName,
        [Parameter(Mandatory = $true)][string]$SqlEndpoint,
        [Parameter(Mandatory = $true)][string]$GoldDatabase,
        [Parameter(Mandatory = $true)][string]$ModelConnectionString
    )

    $temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-" + [guid]::NewGuid())
    $semanticModelDirectory = Join-Path $temporaryDirectory "${SemanticModelName}.SemanticModel"
    $reportDirectory = Join-Path $temporaryDirectory "${ReportName}.Report"
    Copy-Item -LiteralPath $SemanticModelSourcePath -Destination $semanticModelDirectory -Recurse
    Copy-Item -LiteralPath $ReportSourcePath -Destination $reportDirectory -Recurse
    Remove-Item -LiteralPath (Join-Path $semanticModelDirectory '.platform') -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $reportDirectory '.platform') -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $semanticModelDirectory '.pbi') -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $reportDirectory '.pbi') -Recurse -Force -ErrorAction SilentlyContinue

    $expressionsPath = Join-Path $semanticModelDirectory 'definition/expressions.tmdl'
    $expressions = Get-Content -LiteralPath $expressionsPath -Raw -Encoding UTF8
    $escapedEndpoint = $SqlEndpoint.Replace('\', '\\').Replace('"', '\"')
    $escapedDatabase = $GoldDatabase.Replace('\', '\\').Replace('"', '\"')
    $expressions = [regex]::Replace($expressions, 'expression GoldSqlEndpoint = "[^"]*"',
        "expression GoldSqlEndpoint = `"$escapedEndpoint`"")
    $expressions = [regex]::Replace($expressions, 'expression GoldDatabase = "[^"]*"',
        "expression GoldDatabase = `"$escapedDatabase`"")
    if ($expressions -notmatch "expression GoldSqlEndpoint = `"$([regex]::Escape($escapedEndpoint))`"") {
        throw 'Could not configure GoldSqlEndpoint in the semantic model.'
    }

    $definitionPath = Join-Path $reportDirectory 'definition.pbir'
    $reportDefinition = Get-Content -LiteralPath $definitionPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Set-JsonProperty -InputObject $reportDefinition -Name 'datasetReference' -Value ([pscustomobject]@{
        byConnection = [pscustomobject]@{ connectionString = $ModelConnectionString }
    })

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($expressionsPath, $expressions, $utf8NoBom)
    [System.IO.File]::WriteAllText($definitionPath,
        ($reportDefinition | ConvertTo-Json -Depth 20), $utf8NoBom)

    return [pscustomobject]@{
        Root = $temporaryDirectory
        SemanticModelDirectory = $semanticModelDirectory
        ReportDirectory = $reportDirectory
    }
}

function Get-LakehouseSqlEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceId,
        [Parameter(Mandatory = $true)][string]$LakehouseId,
        [Parameter(Mandatory = $true)][string]$LakehouseName
    )

    for ($attempt = 1; $attempt -le 40; $attempt++) {
        $response = (Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId/lakehouses/$LakehouseId", '-X', 'get') -ReturnOutput) | ConvertFrom-Json
        $lakehouseProperties = Get-OptionalProperty -InputObject $response.text -Name 'properties'
        $properties = Get-OptionalProperty -InputObject $lakehouseProperties -Name 'sqlEndpointProperties'
        $status = Get-OptionalProperty -InputObject $properties -Name 'provisioningStatus'
        $connectionString = Get-OptionalProperty -InputObject $properties -Name 'connectionString'
        if ($status -eq 'Success' -and $connectionString) {
            return [string]$connectionString
        }
        if ($status -eq 'Failed') {
            throw "The SQL endpoint for $LakehouseName failed to provision."
        }
        if ($attempt -lt 40) { Start-Sleep -Seconds 5 }
    }
    throw "The SQL endpoint for $LakehouseName is still provisioning."
}

function Initialize-SemanticModelConnection {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceId,
        [Parameter(Mandatory = $true)][string]$SemanticModelId,
        [Parameter(Mandatory = $true)][string]$ConnectionName,
        [Parameter(Mandatory = $true)][string]$SqlEndpoint,
        [Parameter(Mandatory = $true)][string]$Database
    )

    # StrictMode turns a missing property into a terminating error, and a workspace without
    # a provisioned identity simply omits `workspaceIdentity` from the response.
    $workspace = (Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId", '-X', 'get') -ReturnOutput) | ConvertFrom-Json
    $identity = Get-OptionalProperty -InputObject $workspace.text -Name 'workspaceIdentity'
    if (-not $identity) {
        Write-InstallerStatus -Type Info -Message 'Provisioning the workspace identity'
        Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId/provisionIdentity", '-X', 'post')
        for ($attempt = 1; $attempt -le 30 -and -not $identity; $attempt++) {
            Start-Sleep -Seconds 5
            $workspace = (Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId", '-X', 'get') -ReturnOutput) | ConvertFrom-Json
            $identity = Get-OptionalProperty -InputObject $workspace.text -Name 'workspaceIdentity'
        }
        if (-not $identity) { throw 'Workspace identity provisioning did not complete.' }
    }

    $assignments = (Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId/roleAssignments", '-X', 'get') -ReturnOutput) | ConvertFrom-Json
    $existingAssignments = @(Get-OptionalProperty -InputObject $assignments.text -Name 'value')
    if (-not ($existingAssignments | Where-Object { $_.principal.id -eq $identity.servicePrincipalId })) {
        $roleBody = @{ principal = @{ id = $identity.servicePrincipalId; type = 'ServicePrincipal' }; role = 'Viewer' } | ConvertTo-Json -Compress
        $roleFile = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-role-" + [guid]::NewGuid() + '.json')
        try {
            [System.IO.File]::WriteAllText($roleFile, $roleBody, [System.Text.UTF8Encoding]::new($false))
            Invoke-FabricCli -Arguments @('api', "workspaces/$WorkspaceId/roleAssignments", '-X', 'post', '-i', $roleFile)
        }
        finally { Remove-Item $roleFile -Force -ErrorAction SilentlyContinue }
    }

    $connectionPath = "$SqlEndpoint;$Database"
    $connections = (Invoke-FabricCli -Arguments @('api', 'connections', '-X', 'get') -ReturnOutput) | ConvertFrom-Json
    # Type and path alone do not identify a usable connection: a personal or OAuth
    # connection over the same endpoint matches just as well and cannot serve an unattended
    # refresh, so only a shareable connection holding workspace-identity credentials is reused.
    $connection = @(Get-OptionalProperty -InputObject $connections.text -Name 'value') | Where-Object {
        $details = Get-OptionalProperty -InputObject $_ -Name 'connectionDetails'
        $credentialType = Get-OptionalProperty -InputObject (Get-OptionalProperty -InputObject $_ -Name 'credentialDetails') -Name 'credentialType'
        (Get-OptionalProperty -InputObject $details -Name 'type') -eq 'SQL' -and
        (Get-OptionalProperty -InputObject $details -Name 'path') -ieq $connectionPath -and
        (Get-OptionalProperty -InputObject $_ -Name 'connectivityType') -eq 'ShareableCloud' -and
        $credentialType -eq 'WorkspaceIdentity'
    } | Select-Object -First 1
    if (-not $connection) {
        $connectionBody = @{
            connectivityType = 'ShareableCloud'
            displayName = $ConnectionName
            connectionDetails = @{
                type = 'SQL'; creationMethod = 'Sql'; parameters = @(
                    @{ dataType = 'Text'; name = 'server'; value = $SqlEndpoint }
                    @{ dataType = 'Text'; name = 'database'; value = $Database }
                )
            }
            privacyLevel = 'Organizational'
            credentialDetails = @{
                singleSignOnType = 'None'; connectionEncryption = 'Encrypted'; skipTestConnection = $false
                credentials = @{ credentialType = 'WorkspaceIdentity' }
            }
        } | ConvertTo-Json -Depth 10 -Compress
        $connectionFile = Join-Path ([System.IO.Path]::GetTempPath()) ("EducationFabric-connection-" + [guid]::NewGuid() + '.json')
        try {
            [System.IO.File]::WriteAllText($connectionFile, $connectionBody, [System.Text.UTF8Encoding]::new($false))
            $created = (Invoke-FabricCli -Arguments @('api', 'connections', '-X', 'post', '-i', $connectionFile) -ReturnOutput) | ConvertFrom-Json
            # `fab api` exits zero for an HTTP error, so the status code has to be checked here.
            # Connection names are unique across the tenant, which is why the name carries the
            # workspace: a connection from another workspace's deployment would otherwise collide.
            $statusCode = [int](Get-OptionalProperty -InputObject $created -Name 'status_code')
            if ($statusCode -lt 200 -or $statusCode -ge 300) {
                throw "Could not create SQL connection ${ConnectionName}: HTTP $statusCode $($created.text | ConvertTo-Json -Compress -Depth 5)"
            }
            $connection = $created.text
            Write-InstallerStatus -Type Success -Message "Created SQL connection $ConnectionName"
        }
        finally { Remove-Item $connectionFile -Force -ErrorAction SilentlyContinue }
    }

    $gatewayId = Get-OptionalProperty -InputObject $connection -Name 'gatewayId'
    $connectionId = Get-OptionalProperty -InputObject $connection -Name 'id'
    if (-not $connectionId) {
        throw "Could not resolve the SQL connection for $Database."
    }

    # Binding, refreshing and updating parameters are Power BI endpoints rather than Fabric
    # ones. The Fabric CLI already holds a token for that audience, so `-A powerbi` reuses
    # the single `fab auth login` identity instead of requiring a second sign-in through Azure CLI.
    $bindBody = @{ gatewayObjectId = $gatewayId; datasourceObjectIds = @($connectionId) } | ConvertTo-Json -Compress
    $null = Invoke-PowerBiApi -Endpoint "groups/$WorkspaceId/datasets/$SemanticModelId/Default.BindToGateway" -Method 'post' -Body $bindBody
    Write-InstallerStatus -Type Success -Message 'Bound the semantic model to the Gold SQL connection.'
}

function Get-SemanticModelRefreshHistory {
    param(
        [Parameter(Mandatory = $true)][string]$Endpoint
    )

    $refreshes = Invoke-PowerBiApi -Endpoint $Endpoint -Params '$top=20'
    return @(Get-OptionalProperty -InputObject (Get-OptionalProperty -InputObject $refreshes -Name 'text') -Name 'value')
}

function Invoke-SemanticModelRefresh {
    <#
        Submit a refresh and wait for the one this call started.

        The refresh POST does not always return a `RequestId` header. Falling back to the
        newest history entry then accepts a refresh that finished before this call, which
        reports success while the submitted refresh is still running or has failed, so the
        history is captured first and an unheaded refresh is identified as the request that
        appears afterwards.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceId,
        [Parameter(Mandatory = $true)][string]$SemanticModelId,
        [Parameter(Mandatory = $false)][string[]]$Tables,
        [Parameter(Mandatory = $false)][string]$Description = 'Semantic model refresh'
    )

    $endpoint = "groups/$WorkspaceId/datasets/$SemanticModelId/refreshes"
    if ($Tables) {
        $body = @{ type = 'full'; notifyOption = 'NoNotification'; objects = @($Tables | ForEach-Object { @{ table = $_ } }) } |
            ConvertTo-Json -Depth 5 -Compress
    }
    else {
        $body = '{"notifyOption":"NoNotification"}'
    }

    $knownRequestIds = @(Get-SemanticModelRefreshHistory -Endpoint $endpoint |
        ForEach-Object { [string](Get-OptionalProperty -InputObject $_ -Name 'requestId') } |
        Where-Object { $_ })

    $refreshResponse = Invoke-PowerBiApi -Endpoint $endpoint -Method 'post' -Body $body -ShowHeaders
    $refreshHeaders = Get-OptionalProperty -InputObject $refreshResponse -Name 'headers'
    $refreshRequestId = [string](Get-OptionalProperty -InputObject $refreshHeaders -Name 'RequestId')

    for ($attempt = 1; $attempt -le 120; $attempt++) {
        $history = @(Get-SemanticModelRefreshHistory -Endpoint $endpoint)
        if (-not $refreshRequestId) {
            $submitted = $history | Where-Object {
                $id = [string](Get-OptionalProperty -InputObject $_ -Name 'requestId')
                $id -and ($knownRequestIds -notcontains $id)
            } | Select-Object -First 1
            if ($submitted) { $refreshRequestId = [string](Get-OptionalProperty -InputObject $submitted -Name 'requestId') }
        }
        if ($refreshRequestId) {
            $refresh = $history | Where-Object {
                [string](Get-OptionalProperty -InputObject $_ -Name 'requestId') -eq $refreshRequestId
            } | Select-Object -First 1
            $status = [string](Get-OptionalProperty -InputObject $refresh -Name 'status')
            if ($status -eq 'Completed') {
                Write-InstallerStatus -Type Success -Message "$Description $refreshRequestId completed."
                return
            }
            # `Disabled` is terminal alongside `Failed` and `Cancelled`. Treating it as still
            # running only bought a ten-minute wait and then a misleading timeout.
            if ($status -in @('Failed', 'Cancelled', 'Disabled')) {
                $detail = Get-OptionalProperty -InputObject $refresh -Name 'serviceExceptionJson'
                throw "$Description $($status.ToLowerInvariant()). $detail"
            }
        }
        if ($attempt -lt 120) { Start-Sleep -Seconds 5 }
    }
    throw "$Description is still running after ten minutes."
}

function Set-SemanticModelParameter {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceId,
        [Parameter(Mandatory = $true)][string]$SemanticModelId,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value
    )

    $body = @{ updateDetails = @(@{ name = $Name; newValue = $Value }) } | ConvertTo-Json -Depth 5 -Compress
    $null = Invoke-PowerBiApi -Endpoint "groups/$WorkspaceId/datasets/$SemanticModelId/Default.UpdateParameters" `
        -Method 'post' -Body $body
}

function Get-PublishedGoldSnapshot {
    <#
        Resolve the snapshot the Gold Lakehouse currently publishes.

        The Gold schema notebook creates `GoldPublication` empty, so the table existing
        proves nothing about whether a snapshot was ever published. Refreshing just that
        table and reading it back answers both questions at once: whether a publication row
        exists at all, and which snapshot the rest of the model has to be pinned to.

        A tenant may block the DAX query endpoint. That is reported rather than fatal: the
        installer falls back to the model resolving the newest snapshot per table.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceId,
        [Parameter(Mandatory = $true)][string]$SemanticModelId
    )

    try {
        Invoke-SemanticModelRefresh -WorkspaceId $WorkspaceId -SemanticModelId $SemanticModelId `
            -Tables @('GoldPublication') -Description 'GoldPublication refresh'

        $query = "EVALUATE TOPN ( 1, SELECTCOLUMNS ( 'GoldPublication', \""SnapshotId\"", 'GoldPublication'[snapshot_id], \""PublishedAt\"", 'GoldPublication'[Published at] ), [PublishedAt], DESC )"
        $body = "{""queries"":[{""query"":""$query""}],""serializerSettings"":{""includeNulls"":true}}"
        $response = Invoke-PowerBiApi -Endpoint "groups/$WorkspaceId/datasets/$SemanticModelId/executeQueries" `
            -Method 'post' -Body $body
        $results = @(Get-OptionalProperty -InputObject (Get-OptionalProperty -InputObject $response -Name 'text') -Name 'results')
        $tables = @(Get-OptionalProperty -InputObject ($results | Select-Object -First 1) -Name 'tables')
        $rows = @(Get-OptionalProperty -InputObject ($tables | Select-Object -First 1) -Name 'rows')
        $row = $rows | Select-Object -First 1
        $snapshotId = [string](Get-OptionalProperty -InputObject $row -Name '[SnapshotId]')
        return [pscustomobject]@{ Resolved = $true; HasPublication = [bool]$snapshotId; SnapshotId = $snapshotId }
    }
    catch {
        Write-InstallerStatus -Type Warning -Message "Could not read GoldPublication from the semantic model: $($_.Exception.Message)"
        return [pscustomobject]@{ Resolved = $false; HasPublication = $true; SnapshotId = '' }
    }
}

function Get-FabricItemId {
    <#
        Resolve an item ID after creation or import. The CLI caches workspace items, so a
        newly created item can briefly appear to be missing.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [int]$Attempts = 10
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $id = Get-FabricProperty -Path $Path -Property 'id'
        }
        catch {
            $lastError = $_
            $id = $null
        }
        if ($id -match '^[0-9a-fA-F-]{36}$') { return $id }
        if ($attempt -lt $Attempts) { Start-Sleep -Seconds ([Math]::Min($attempt * 2, 10)) }
    }
        throw "Could not resolve the item ID for $Path after $Attempts attempts. $lastError"
}

function New-FabricLakehouse {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (Test-FabricPath -Path $Path) {
        Write-InstallerStatus -Type Success -Message "Reusing Lakehouse $Name"
    }
    else {
        Write-InstallerStatus -Type Info -Message "Creating Lakehouse $Name"
        Invoke-FabricCli -Arguments @('mkdir', $Path)
    }
    return Get-FabricItemId -Path $Path
}

function Invoke-FabricItemJob {
    <#
        Submit one job and poll it to a terminal state. `fab job run` can exit zero for a
        failed job, so the exit code alone is not proof of success.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [ValidateSet('RunNotebook', 'Pipeline')]
        [string]$JobType,

        [Parameter(Mandatory = $false)]
        [int]$TimeoutSeconds = 3600
    )

    $workspaceId = Get-FabricItemId -Path $workspacePath
    $itemId = Get-FabricItemId -Path $Path
    $endpoint = "workspaces/$workspaceId/items/$itemId/jobs/instances?jobType=$JobType"
    $response = (Invoke-FabricCli -Arguments @('api', $endpoint, '-X', 'post', '--show_headers') -ReturnOutput) | ConvertFrom-Json

    $jobId = $null
    $location = if ($response.headers -and $response.headers.PSObject.Properties['Location']) {
        [string]$response.headers.Location
    }
    else {
        ''
    }
    if ($location -match '/jobs/instances/([0-9a-fA-F-]{36})') {
        $jobId = $Matches[1]
    }
    elseif ($response.text -and $response.text -isnot [string] -and $response.text.PSObject.Properties['id']) {
        $jobId = [string]$response.text.id
    }
    if ($jobId -notmatch '^[0-9a-fA-F-]{36}$') { throw "Job submission for $Path returned no job ID." }
    Write-InstallerStatus -Type Info -Message "Submitted job $jobId for $Path"

    $watch = [diagnostics.stopwatch]::StartNew()
    while ($true) {
        $jobResponse = (Invoke-FabricCli -Arguments @('api', "workspaces/$workspaceId/items/$itemId/jobs/instances/$jobId") -ReturnOutput) | ConvertFrom-Json
        $job = $jobResponse.text
        if (-not $job -or $job -is [string] -or -not $job.PSObject.Properties['status']) {
            throw "Fabric returned an invalid status response for job $jobId."
        }
        $status = [string]$job.status
        if ($status -eq 'Completed') {
            Write-InstallerStatus -Type Success -Message "Job $jobId completed."
            return
        }
        if ($status -in @('Failed', 'Cancelled', 'Canceled', 'Disabled', 'Deduped')) {
            $reason = if ($job.failureReason.message) { $job.failureReason.message } else { $job.failureReason | ConvertTo-Json -Compress }
            throw "Job $jobId for $Path ended unsuccessfully: $status. $reason"
        }
        if ($status -notin @('NotStarted', 'InProgress', 'Running', 'Queued')) {
            Write-Verbose "Job $jobId returned unrecognized nonterminal status '$status'; polling continues until timeout."
        }
        if ($watch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            throw "Job $jobId for $Path timed out with status $status; completion is not verified."
        }
        Start-Sleep -Seconds 5
    }
}

$script:KnownLakehouseDirectories = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

function New-LakehouseDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetLakehousePath,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    # OneLake can briefly report a folder it has just created as missing, so a folder this run
    # already created or found is remembered, and "already exists" from mkdir counts as done.
    $currentPath = "$TargetLakehousePath/Files"
    foreach ($segment in $RelativePath.Split('/', [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $currentPath = "$currentPath/$segment"
        if ($script:KnownLakehouseDirectories.Contains($currentPath)) {
            continue
        }
        if (-not (Test-FabricPath -Path $currentPath)) {
            try {
                Invoke-FabricCli -Arguments @('mkdir', $currentPath)
            }
            catch {
                if ($_.Exception.Message -notmatch 'PathAlreadyExists') {
                    throw
                }
            }
        }
        $null = $script:KnownLakehouseDirectories.Add($currentPath)
    }

    return $currentPath
}

function Copy-LandingFiles {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo[]]$CsvFiles
    )

    $destinationRoot = New-LakehouseDirectory -TargetLakehousePath $lakehousePath -RelativePath $landingPath

    $files = @((Get-Item -LiteralPath $manifestPath)) + $CsvFiles
    for ($index = 0; $index -lt $files.Count; $index++) {
        $file = $files[$index]
        $relativePath = [System.IO.Path]::GetRelativePath($sampleDataPath, $file.FullName).Replace('\', '/')
        $relativeDirectory = Split-Path -Parent $relativePath
        if ($relativeDirectory) {
            $null = New-LakehouseDirectory -TargetLakehousePath $lakehousePath -RelativePath "$landingPath/$($relativeDirectory.Replace('\', '/'))"
        }

        $destinationFile = "$destinationRoot/$relativePath"
        Write-Progress -Activity 'Uploading Bronze source package' -Status $relativePath `
            -PercentComplete ((($index + 1) / $files.Count) * 100)
        # A single OneLake connection timeout should not abandon a long upload.
        for ($attempt = 1; ; $attempt++) {
            try {
                Invoke-FabricCli -Arguments @('copy', $file.FullName, $destinationFile, '--force')
                break
            }
            catch {
                if ($attempt -ge 3) {
                    throw
                }
                Write-InstallerStatus -Type Warning -Message "Upload of $relativePath failed (attempt $attempt of 3); retrying."
                Start-Sleep -Seconds (15 * $attempt)
            }
        }
    }
    Write-Progress -Activity 'Uploading Bronze source package' -Completed
    Write-InstallerStatus -Type Success -Message "Uploaded $($files.Count) Bronze files."
}

if (-not $script:interactiveSession) {
    Write-InstallerBanner
}
Write-InstallerPlan
if ($script:interactiveSession -and -not (Test-InstallerConfirmation -Prompt 'Continue with this plan?' -Default $PlanOnly)) {
    Write-InstallerStatus -Type Warning -Message 'Installation cancelled. No changes were made.'
    return
}

Write-InstallerSection -Title 'Validate local package'
$csvFiles = Test-LocalArtifacts
Write-InstallerStatus -Type Success -Message 'Validated 28 CSV files, manifest, seven notebooks, and the end-to-end pipeline.'

if ($PlanOnly) {
    $preparedNotebooks = @(
        New-PreparedNotebook -SourcePath $bronzeSchemaNotebookPath -ItemName $bronzeSchemaNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{BRONZE_LAKEHOUSE_ID}' -LakehouseName $lakehouseName
        New-PreparedNotebook -SourcePath $notebookPath -ItemName $notebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{BRONZE_LAKEHOUSE_ID}' -LakehouseName $lakehouseName
        New-PreparedNotebook -SourcePath $silverNotebookPath -ItemName $silverNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{SILVER_LAKEHOUSE_ID}' -LakehouseName $silverLakehouseName
        New-PreparedNotebook -SourcePath $transformNotebookPath -ItemName $transformNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{SILVER_LAKEHOUSE_ID}' -LakehouseName $silverLakehouseName -AdditionalLakehouseIds @('{BRONZE_LAKEHOUSE_ID}') -ParameterValues @{ bronze_lakehouse_name = "`"$lakehouseName`"" }
        New-PreparedNotebook -SourcePath $configNotebookPath -ItemName $configNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{GOLD_LAKEHOUSE_ID}' -LakehouseName $goldLakehouseName -Replacements (Get-ConfigReplacements)
        New-PreparedNotebook -SourcePath $goldNotebookPath -ItemName $goldNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{GOLD_LAKEHOUSE_ID}' -LakehouseName $goldLakehouseName -Replacements (Get-ConfigReplacements)
        New-PreparedNotebook -SourcePath $enrichmentNotebookPath -ItemName $enrichmentNotebookName -WorkspaceId '{WORKSPACE_ID}' -LakehouseId '{GOLD_LAKEHOUSE_ID}' -LakehouseName $goldLakehouseName -AdditionalLakehouseIds @('{SILVER_LAKEHOUSE_ID}') -Replacements (Get-ConfigReplacements)
    )
    $preparedPipeline = New-PreparedPipeline -SourcePath $processingPipelinePath -ItemName $processingPipelineName -Replacements @{
        '{WORKSPACE_ID}' = [guid]::Empty.ToString()
        '{BRONZE_CREATE_SCHEMA_NOTEBOOK_ID}' = [guid]::Empty.ToString()
        '{BRONZE_INGESTION_NOTEBOOK_ID}' = [guid]::Empty.ToString()
        '{SILVER_CREATE_SCHEMA_NOTEBOOK_ID}' = [guid]::Empty.ToString()
        '{BRONZE_TO_SILVER_NOTEBOOK_ID}' = [guid]::Empty.ToString()
        '{GOLD_CREATE_SCHEMA_NOTEBOOK_ID}' = [guid]::Empty.ToString()
        '{SILVER_TO_GOLD_ENRICHMENT_NOTEBOOK_ID}' = [guid]::Empty.ToString()
    }
    $preparedReporting = New-PreparedReportingItems `
        -SemanticModelSourcePath $semanticModelSourcePath `
        -ReportSourcePath $reportSourcePath `
        -SemanticModelName $semanticModelName `
        -ReportName $reportName `
        -SqlEndpoint 'placeholder.datawarehouse.fabric.microsoft.com' `
        -GoldDatabase $goldLakehouseName `
        -ModelConnectionString (Get-ModelConnectionString -SemanticModelName $semanticModelName -SemanticModelId ([guid]::Empty.ToString()))
    try {
        foreach ($preparedNotebook in $preparedNotebooks) {
            $preparedPath = Join-Path $preparedNotebook.Directory 'notebook-content.ipynb'
            $preparedContent = Get-Content -LiteralPath $preparedPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $dependency = $preparedContent.metadata.dependencies.lakehouse
            if (-not $dependency.default_lakehouse_name) {
                throw 'Prepared notebook has no default Lakehouse name.'
            }
            if ($dependency.known_lakehouses -isnot [array] -or $dependency.known_lakehouses.Count -lt 1) {
                throw 'Prepared notebook known_lakehouses must be a non-empty JSON array.'
            }
            $parameterCell = $preparedContent.cells | Where-Object {
                $_.metadata.PSObject.Properties['tags'] -and $_.metadata.tags -contains 'parameters'
            } | Select-Object -First 1
            if (-not $parameterCell) {
                throw 'Prepared notebook does not contain a parameter cell.'
            }
            # A deployment placeholder that survives substitution means the notebook would run
            # against the wrong environment. The reporting period is exempt when none was
            # supplied: it stays unresolved on purpose and the notebook guard blocks the run.
            $unresolved = if ($PeriodStart) { '\{(?:SILVER|GOLD|PERIOD)_[A-Z_]+\}' } else { '\{(?:SILVER|GOLD)_[A-Z_]+\}' }
            if (($preparedContent.cells.source -join "`n") -cmatch $unresolved) {
                throw "Prepared notebook still contains an unresolved deployment placeholder: $($Matches[0])"
            }
            foreach ($codeCell in @($preparedContent.cells | Where-Object cell_type -eq 'code')) {
                $cellCode = $codeCell.source -join ''
                if ($cellCode.TrimStart().StartsWith('%')) { continue }
                $tempCodePath = Join-Path $preparedNotebook.Root ([guid]::NewGuid().ToString() + '.py')
                [System.IO.File]::WriteAllText($tempCodePath, $cellCode, [System.Text.UTF8Encoding]::new($false))
                & $script:pythonPath -m py_compile $tempCodePath
                if ($LASTEXITCODE -ne 0) {
                    throw "Prepared notebook contains invalid Python: $preparedPath"
                }
            }
        }
        $preparedExpressions = Get-Content -LiteralPath (Join-Path $preparedReporting.SemanticModelDirectory 'definition/expressions.tmdl') -Raw
        if ($preparedExpressions -notmatch 'placeholder\.datawarehouse\.fabric\.microsoft\.com' -or
                $preparedExpressions -notmatch ([regex]::Escape($goldLakehouseName))) {
            throw 'Prepared semantic model does not contain the deployment parameters.'
        }
        $preparedReport = Get-Content -LiteralPath (Join-Path $preparedReporting.ReportDirectory 'definition.pbir') -Raw | ConvertFrom-Json
        # Fabric rejects a byPath report definition, and its byConnection schema allows
        # connectionString only, so anything else here would fail at import time.
        if ($preparedReport.datasetReference.PSObject.Properties['byPath']) {
            throw 'Prepared report still uses a byPath dataset reference, which Fabric rejects on import.'
        }
        $reportConnection = $preparedReport.datasetReference.byConnection
        if (@($reportConnection.PSObject.Properties.Name) -ne @('connectionString')) {
            throw 'Prepared report byConnection must carry connectionString and nothing else.'
        }
        if ($reportConnection.connectionString -notmatch [regex]::Escape("Initial Catalog=$semanticModelName;") -or
                $reportConnection.connectionString -notmatch 'semanticModelId=[0-9a-fA-F-]{36}$') {
            throw 'Prepared report does not reference the deployed semantic model.'
        }
    }
    finally {
        foreach ($preparedNotebook in $preparedNotebooks) {
            Remove-Item -LiteralPath $preparedNotebook.Root -Recurse -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $preparedPipeline.Root -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $preparedReporting.Root -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-InstallerStatus -Type Success -Message 'Preview passed. No Fabric resources were changed.'
    return
}

if (-not (Get-Command fab -ErrorAction SilentlyContinue)) {
    throw 'Microsoft Fabric CLI is not installed. See https://aka.ms/fabric-cli.'
}

& fab auth status *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Fabric CLI is not authenticated. Run: fab auth login'
}
if (-not (Test-FabricPath -Path $workspacePath)) {
    throw "Fabric workspace not found or not accessible: $WorkspaceName"
}

Write-InstallerSection -Title 'Connect to Fabric'
$workspaceId = Get-FabricProperty -Path $workspacePath -Property 'id'
Write-InstallerStatus -Type Success -Message "Connected to workspace $WorkspaceName"

if ($solutionFolderName -and -not (Test-FabricPath -Path $artifactRootPath)) {
    Write-InstallerStatus -Type Info -Message "Creating solution folder $solutionFolderName"
    Invoke-FabricCli -Arguments @('mkdir', $artifactRootPath)
}

# Fail upgrade compatibility checks before creating or importing anything.
if (($RunGoldCreateSchemaNotebook -or $RunEndToEndPipeline) -and
        -not $OverwriteSharedConfigNotebook -and
        (Test-FabricPath -Path $configNotebookFabricPath)) {
    throw "Gold execution requires the managed $configNotebookName definition. Rerun with -OverwriteSharedConfigNotebook after reviewing the deployment plan."
}

# Preserve a reporting period that is already configured, unless this run supplies one.
if (-not $PeriodStart) {
    $script:effectivePeriod = Get-DeployedReportingPeriod -Path $enrichmentNotebookFabricPath
    if ($script:effectivePeriod) {
        Write-InstallerStatus -Type Success -Message "Preserving reporting period [$($script:effectivePeriod.Start), $($script:effectivePeriod.End))"
    }
    else {
        Write-InstallerStatus -Type Warning -Message 'No reporting period is configured; Gold enrichment will remain disabled.'
    }
}

Write-InstallerSection -Title 'Provision Lakehouses'
$lakehouseId = New-FabricLakehouse -Name $lakehouseName -Path $lakehousePath
$silverLakehouseId = New-FabricLakehouse -Name $silverLakehouseName -Path $silverLakehousePath
$goldLakehouseId = New-FabricLakehouse -Name $goldLakehouseName -Path $goldLakehousePath

if (-not $SkipBronzeDataUpload) {
    Write-InstallerSection -Title 'Upload Bronze data'
    Copy-LandingFiles -CsvFiles $csvFiles
}

Write-InstallerSection -Title 'Deploy notebooks'
$preparedBronzeSchemaNotebook = New-PreparedNotebook -SourcePath $bronzeSchemaNotebookPath -ItemName $bronzeSchemaNotebookName -WorkspaceId $workspaceId -LakehouseId $lakehouseId -LakehouseName $lakehouseName
try {
    Write-InstallerStatus -Type Info -Message "Importing notebook $bronzeSchemaNotebookName"
    Invoke-FabricCli -Arguments @('import', $bronzeSchemaNotebookFabricPath, '--input', $preparedBronzeSchemaNotebook.Directory, '--force')

    if ($RunNotebook -and -not $RunEndToEndPipeline) {
        Write-InstallerStatus -Type Info -Message "Running notebook $bronzeSchemaNotebookName"
        Invoke-FabricItemJob -Path $bronzeSchemaNotebookFabricPath -JobType 'RunNotebook'
    }
}
finally {
    Remove-Item -LiteralPath $preparedBronzeSchemaNotebook.Root -Recurse -Force -ErrorAction SilentlyContinue
}

$preparedNotebook = New-PreparedNotebook -SourcePath $notebookPath -ItemName $notebookName -WorkspaceId $workspaceId -LakehouseId $lakehouseId -LakehouseName $lakehouseName
try {
    Write-InstallerStatus -Type Info -Message "Importing notebook $notebookName"
    Invoke-FabricCli -Arguments @('import', $notebookFabricPath, '--input', $preparedNotebook.Directory, '--force')

    if ($RunNotebook -and -not $RunEndToEndPipeline) {
        Write-InstallerStatus -Type Info -Message "Running notebook $notebookName"
        Invoke-FabricItemJob -Path $notebookFabricPath -JobType 'RunNotebook'
    }
}
finally {
    Remove-Item -LiteralPath $preparedNotebook.Root -Recurse -Force -ErrorAction SilentlyContinue
}

$preparedSilverNotebook = New-PreparedNotebook -SourcePath $silverNotebookPath -ItemName $silverNotebookName -WorkspaceId $workspaceId -LakehouseId $silverLakehouseId -LakehouseName $silverLakehouseName
try {
    Write-InstallerStatus -Type Info -Message "Importing notebook $silverNotebookName"
    Invoke-FabricCli -Arguments @('import', $silverNotebookFabricPath, '--input', $preparedSilverNotebook.Directory, '--force')

    if ($RunSilverCreateSchemaNotebook -and -not $RunEndToEndPipeline) {
        Write-InstallerStatus -Type Info -Message "Running notebook $silverNotebookName"
        Invoke-FabricItemJob -Path $silverNotebookFabricPath -JobType 'RunNotebook'
    }
}
finally {
    Remove-Item -LiteralPath $preparedSilverNotebook.Root -Recurse -Force -ErrorAction SilentlyContinue
}

$preparedTransformNotebook = New-PreparedNotebook -SourcePath $transformNotebookPath -ItemName $transformNotebookName `
    -WorkspaceId $workspaceId -LakehouseId $silverLakehouseId -LakehouseName $silverLakehouseName `
    -AdditionalLakehouseIds @($lakehouseId) -ParameterValues @{ bronze_lakehouse_name = "`"$lakehouseName`"" }
try {
    Write-InstallerStatus -Type Info -Message "Importing notebook $transformNotebookName"
    Invoke-FabricCli -Arguments @('import', $transformNotebookFabricPath, '--input', $preparedTransformNotebook.Directory, '--force')

    if ($RunSilverTransformNotebook -and -not $RunEndToEndPipeline) {
        Write-InstallerStatus -Type Info -Message "Running notebook $transformNotebookName"
        Invoke-FabricItemJob -Path $transformNotebookFabricPath -JobType 'RunNotebook'
    }
}
finally {
    Remove-Item -LiteralPath $preparedTransformNotebook.Root -Recurse -Force -ErrorAction SilentlyContinue
}

$configReplacements = Get-ConfigReplacements
Write-InstallerSection -Title 'Deploy Gold artifacts'
$goldNotebookSpecs = @(
    @{ SourcePath = $configNotebookPath; ItemName = $configNotebookName; FabricPath = $configNotebookFabricPath; Additional = @() }
    @{ SourcePath = $goldNotebookPath; ItemName = $goldNotebookName; FabricPath = $goldNotebookFabricPath; Additional = @() }
    @{ SourcePath = $enrichmentNotebookPath; ItemName = $enrichmentNotebookName; FabricPath = $enrichmentNotebookFabricPath; Additional = @($silverLakehouseId) }
)
foreach ($spec in $goldNotebookSpecs) {
    # The shared configuration notebook may carry local edits, so it is never replaced
    # silently. Other notebooks are generated artifacts and are safe to overwrite.
    if ($spec.ItemName -eq $configNotebookName -and -not $OverwriteSharedConfigNotebook) {
        if (Test-FabricPath -Path $spec.FabricPath) {
            if ($RunGoldCreateSchemaNotebook -or $RunEndToEndPipeline) {
                throw "Gold execution requires the managed $configNotebookName definition. Rerun with -OverwriteSharedConfigNotebook after reviewing the deployment plan."
            }
            Write-InstallerStatus -Type Warning -Message "Keeping existing $($spec.ItemName). Use -OverwriteSharedConfigNotebook to replace it."
            continue
        }
    }
    $prepared = New-PreparedNotebook -SourcePath $spec.SourcePath -ItemName $spec.ItemName -WorkspaceId $workspaceId `
        -LakehouseId $goldLakehouseId -LakehouseName $goldLakehouseName -AdditionalLakehouseIds $spec.Additional `
        -Replacements $configReplacements
    try {
        Write-InstallerStatus -Type Info -Message "Importing notebook $($spec.ItemName)"
        Invoke-FabricCli -Arguments @('import', $spec.FabricPath, '--input', $prepared.Directory, '--force')
    }
    finally {
        Remove-Item -LiteralPath $prepared.Root -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$preparedPipeline = New-PreparedPipeline -SourcePath $processingPipelinePath -ItemName $processingPipelineName -Replacements @{
    '{WORKSPACE_ID}' = $workspaceId
    '{BRONZE_CREATE_SCHEMA_NOTEBOOK_ID}' = (Get-FabricItemId -Path $bronzeSchemaNotebookFabricPath)
    '{BRONZE_INGESTION_NOTEBOOK_ID}' = (Get-FabricItemId -Path $notebookFabricPath)
    '{SILVER_CREATE_SCHEMA_NOTEBOOK_ID}' = (Get-FabricItemId -Path $silverNotebookFabricPath)
    '{BRONZE_TO_SILVER_NOTEBOOK_ID}' = (Get-FabricItemId -Path $transformNotebookFabricPath)
    '{GOLD_CREATE_SCHEMA_NOTEBOOK_ID}' = (Get-FabricItemId -Path $goldNotebookFabricPath)
    '{SILVER_TO_GOLD_ENRICHMENT_NOTEBOOK_ID}' = (Get-FabricItemId -Path $enrichmentNotebookFabricPath)
}
try {
    Write-InstallerStatus -Type Info -Message "Importing pipeline $processingPipelineName"
    Invoke-FabricCli -Arguments @('import', $processingPipelineFabricPath, '--input', $preparedPipeline.Directory, '--force')
}
finally {
    Remove-Item -LiteralPath $preparedPipeline.Root -Recurse -Force -ErrorAction SilentlyContinue
}

if ($RemoveRetiredPipeline -and
    $legacyEnrichmentPipelineFabricPath -ne $processingPipelineFabricPath -and
        (Test-FabricPath -Path $legacyEnrichmentPipelineFabricPath)) {
    $legacyPipelineId = Get-FabricItemId -Path $legacyEnrichmentPipelineFabricPath
    Write-InstallerStatus -Type Info -Message "Removing retired pipeline ${Prefix}SL_GD_Enrichment"
    Invoke-FabricCli -Arguments @('api', "workspaces/$workspaceId/items/$legacyPipelineId", '-X', 'delete')
}

if ($RunGoldCreateSchemaNotebook -and -not $RunEndToEndPipeline) {
    Write-InstallerStatus -Type Info -Message "Running notebook $goldNotebookName"
    Invoke-FabricItemJob -Path $goldNotebookFabricPath -JobType 'RunNotebook'
}

if ($RunEndToEndPipeline) {
    Write-InstallerStatus -Type Info -Message "Running pipeline $processingPipelineName for [$PeriodStart, $PeriodEnd)"
    Invoke-FabricItemJob -Path $processingPipelineFabricPath -JobType 'Pipeline'
}

# Reporting is deployed last because the semantic model imports from Gold. Refreshing it
# before the pipeline has published a snapshot would query tables that do not exist yet.
Write-InstallerSection -Title 'Deploy reporting'
$goldSqlEndpoint = Get-LakehouseSqlEndpoint -WorkspaceId $workspaceId -LakehouseId $goldLakehouseId -LakehouseName $goldLakehouseName

# Fabric binds a report to a remote model by GUID, which only exists once the model is
# imported. The first pass stages and imports the model; the connection string, and with it
# the report, can only be built afterwards.
$preparedModelOnly = New-PreparedReportingItems `
    -SemanticModelSourcePath $semanticModelSourcePath `
    -ReportSourcePath $reportSourcePath `
    -SemanticModelName $semanticModelName `
    -ReportName $reportName `
    -SqlEndpoint $goldSqlEndpoint `
    -GoldDatabase $goldLakehouseName `
    -ModelConnectionString (Get-ModelConnectionString -SemanticModelName $semanticModelName -SemanticModelId ([guid]::Empty.ToString()))
try {
    Write-InstallerStatus -Type Info -Message "Importing semantic model $semanticModelName"
    Invoke-FabricCli -Arguments @('import', $semanticModelFabricPath, '--input', $preparedModelOnly.SemanticModelDirectory, '--force')
}
finally {
    Remove-Item -LiteralPath $preparedModelOnly.Root -Recurse -Force -ErrorAction SilentlyContinue
}
$semanticModelId = Get-FabricItemId -Path $semanticModelFabricPath

$preparedReporting = New-PreparedReportingItems `
    -SemanticModelSourcePath $semanticModelSourcePath `
    -ReportSourcePath $reportSourcePath `
    -SemanticModelName $semanticModelName `
    -ReportName $reportName `
    -SqlEndpoint $goldSqlEndpoint `
    -GoldDatabase $goldLakehouseName `
    -ModelConnectionString (Get-ModelConnectionString -SemanticModelName $semanticModelName -SemanticModelId $semanticModelId)
try {
    Write-InstallerStatus -Type Info -Message "Importing report $reportName"
    Invoke-FabricCli -Arguments @('import', $reportFabricPath, '--input', $preparedReporting.ReportDirectory, '--force')

    # A model that has never been refreshed still deploys; only the refresh needs Gold data.
    # Deploying the items but skipping the refresh keeps a Bronze-only install from failing.
    # The Gold schema notebook creates GoldPublication empty, so the table existing is not
    # evidence of a snapshot: the publication row itself has to be there.
    $noSnapshotWarning = "$goldLakehouseName has no published snapshot yet; $semanticModelName was deployed without a refresh. Rerun with -RunEndToEndPipeline to populate it."
    if (Test-FabricPath -Path "$goldLakehousePath/Tables/GoldPublication") {
        Initialize-SemanticModelConnection -WorkspaceId $workspaceId -SemanticModelId $semanticModelId `
            -ConnectionName "${goldLakehouseName}_SQL ($WorkspaceName)" -SqlEndpoint $goldSqlEndpoint -Database $goldLakehouseName

        $publication = Get-PublishedGoldSnapshot -WorkspaceId $workspaceId -SemanticModelId $semanticModelId
        if (-not $publication.HasPublication) {
            Write-InstallerStatus -Type Warning -Message $noSnapshotWarning
        }
        else {
            # Every Gold table otherwise resolves the newest publication on its own, so a
            # snapshot published mid-refresh would leave earlier tables on the old snapshot
            # and later ones on the new. Pinning the snapshot resolved once above makes the
            # whole refresh load one consistent bundle; clearing it afterwards leaves the
            # model free to pick up the newest snapshot on any later refresh.
            if ($publication.SnapshotId) {
                Set-SemanticModelParameter -WorkspaceId $workspaceId -SemanticModelId $semanticModelId `
                    -Name 'GoldSnapshotId' -Value $publication.SnapshotId
                Write-InstallerStatus -Type Info -Message "Pinned the refresh to Gold snapshot $($publication.SnapshotId.Substring(0, [Math]::Min(12, $publication.SnapshotId.Length)))"
            }
            try {
                Invoke-SemanticModelRefresh -WorkspaceId $workspaceId -SemanticModelId $semanticModelId
                $script:semanticModelRefreshed = $true
            }
            finally {
                if ($publication.SnapshotId) {
                    # A pin left behind would survive into scheduled refreshes, and the
                    # snapshot it names is retired as soon as the next one publishes, so a
                    # failure to clear it has to be visible rather than swallowed. It must
                    # also not replace a refresh failure that is already on its way out.
                    try {
                        Set-SemanticModelParameter -WorkspaceId $workspaceId -SemanticModelId $semanticModelId `
                            -Name 'GoldSnapshotId' -Value ''
                    }
                    catch {
                        Write-InstallerStatus -Type Warning -Message "Could not clear the GoldSnapshotId parameter on $semanticModelName. Set it back to an empty value in Power BI before the next scheduled refresh: $($_.Exception.Message)"
                    }
                }
            }
        }
    }
    else {
        Write-InstallerStatus -Type Warning -Message $noSnapshotWarning
    }
}
finally {
    Remove-Item -LiteralPath $preparedReporting.Root -Recurse -Force -ErrorAction SilentlyContinue
}

Write-InstallerSummary
