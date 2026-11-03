param ( 
    # The name of the workload, used for the Entra App and the workload in the Fabric portal
    [String]$WorkloadName = "Org.MyWorkload",
    # The Entra Application ID for the frontend
    # If not provided, the user will be prompted to enter it or create a new one.
    [String]$FrontendAppId = "00000000-0000-0000-0000-000000000000",
    # The version of the workload, used for the manifest package
    [String]$WorkloadVersion = "1.0.0",
    # Environment that should be build
    [ValidateSet("dev", "test", "prod")]
    [String]$Environment = "prod"
)

if ($FrontendAppId -eq "00000000-0000-0000-0000-000000000000") {
    throw "FrontendAppId must be configured before building a release."
}

$environmentFile = Join-Path $PSScriptRoot "..\..\Workload\.env.$Environment"
if (-not (Test-Path $environmentFile)) {
    throw "Environment file not found: $environmentFile. Run SetupWorkload.ps1 first."
}

$environmentValues = @{}
Get-Content $environmentFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $environmentValues[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$expectedValues = @{
    WORKLOAD_NAME = $WorkloadName
    FRONTEND_APPID = $FrontendAppId
    WORKLOAD_VERSION = $WorkloadVersion
    ITEM_NAMES = "EducationSolution"
}
foreach ($key in $expectedValues.Keys) {
    if ($environmentValues[$key] -ne $expectedValues[$key]) {
        throw ".env.$Environment has $key='$($environmentValues[$key])'; expected '$($expectedValues[$key])'."
    }
}

$frontendUrl = $environmentValues['FRONTEND_URL']
if ([string]::IsNullOrWhiteSpace($frontendUrl)) {
    throw ".env.$Environment must define FRONTEND_URL."
}
if ($Environment -ne 'dev' -and (-not $frontendUrl.StartsWith('https://') -or $frontendUrl.Contains('yourappdomain.com'))) {
    throw ".env.$Environment must use an approved HTTPS FRONTEND_URL, not the generated placeholder domain."
}

$releaseDir = Join-Path $PSScriptRoot "..\..\release"
if ((Test-Path $releaseDir)) {
    Write-Output "Release directory already exists at $releaseDir. Deleting it."
    Remove-Item -Path $releaseDir -Recurse -Force
} 
New-Item -ItemType Directory -Path $releaseDir | Out-Null
$releaseDir = Resolve-Path $releaseDir

###############################################################################
# Creating the release manifest
# 
###############################################################################
# Run BuildManifestPackage.ps1 with absolute path
$buildManifestPackageScript = Join-Path $PSScriptRoot "..\Build\BuildManifestPackage.ps1"
if (Test-Path $buildManifestPackageScript) {
    $buildManifestPackageScript = (Resolve-Path $buildManifestPackageScript).Path
    & $buildManifestPackageScript -Environment $Environment
    if ($LASTEXITCODE -ne 0) {
        throw "Manifest package build failed."
    }
} else {
    Write-Host "BuildManifestPackage.ps1 not found at $buildManifestPackageScript"
    exit 1
}

# Copy the nuget package to the release directory
$buildManifestDir = Join-Path $PSScriptRoot "..\..\build\Manifest"
$releaseManifestDir = Join-Path $releaseDir ""

Move-Item -Path "$buildManifestDir\*.nupkg" -Destination $releaseManifestDir -Force

Write-Host "✅ Moved the new ManifestPackage to $releaseManifestDir." -ForegroundColor Blue


###############################################################################
# Creating the app release
# 
###############################################################################

$releaseAppDir = Join-Path $releaseDir "app"

Write-Host "Building the app release ..."
$workloadDir = Join-Path $PSScriptRoot "..\..\Workload"
Push-Location $workloadDir
try {
    npm run build:$Environment
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed."
    }
    if (!(Test-Path $releaseAppDir)) {
        New-Item -ItemType Directory -Path $releaseAppDir | Out-Null
    }

    # Copy the built files to the release directory
    $buildFrontendDir = Join-Path $PSScriptRoot "..\..\build\Frontend"
    if (Test-Path $buildFrontendDir) {
        Copy-Item -Path "$buildFrontendDir\*" -Destination $releaseAppDir -Recurse -Force
        Write-Host "✅ Copied app release files to $releaseAppDir" -ForegroundColor Blue
    } else {
        Write-Host "⚠️  Warning: Frontend build directory not found at $buildFrontendDir" -ForegroundColor Yellow
    }

} finally {
    Pop-Location
}

Write-Host ""
Write-Host "All release information has been build an is available under the" -ForegroundColor Green
Write-Host "$releaseDir"
Write-Host ""
Write-Host "You can now upload the manifest package and the app release to the Fabric portal." 
Write-Host "The manifest package is located at $releaseManifestDir"
Write-Host ""
write-Host "To upload the app release, to Azure you can use the Deploy scripts."
Write-Host "The app release is located at $releaseAppDir"


