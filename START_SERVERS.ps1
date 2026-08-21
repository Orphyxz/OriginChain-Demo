# OriginChain Demo - Full Server Startup Script
# Run this from PowerShell in the project root directory

$ProjectRoot = $PSScriptRoot
$BlockchainDir = Join-Path $ProjectRoot "blockchain"
$BackendDir = $ProjectRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  OriginChain Demo - Startup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# --- STEP 1: Install blockchain dependencies ---
Write-Host "[1/5] Installing blockchain npm packages..." -ForegroundColor Yellow
Set-Location $BlockchainDir
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: npm install failed. Make sure Node.js is installed." -ForegroundColor Red
    exit 1
}
Write-Host "OK - npm packages installed" -ForegroundColor Green

# --- STEP 2: Compile smart contracts ---
Write-Host ""
Write-Host "[2/5] Compiling smart contracts..." -ForegroundColor Yellow
npx hardhat compile
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Contract compilation failed." -ForegroundColor Red
    exit 1
}
Write-Host "OK - Contracts compiled" -ForegroundColor Green

# --- STEP 3: Install Python backend dependencies ---
Write-Host ""
Write-Host "[3/5] Installing Python backend packages..." -ForegroundColor Yellow
Set-Location $BackendDir
pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed. Make sure Python is installed." -ForegroundColor Red
    exit 1
}
Write-Host "OK - Python packages installed" -ForegroundColor Green

# --- STEP 4: Launch Hardhat node in new window ---
Write-Host ""
Write-Host "[4/5] Starting Hardhat local blockchain node..." -ForegroundColor Yellow
Set-Location $BlockchainDir
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BlockchainDir'; Write-Host 'Hardhat Node Running...' -ForegroundColor Cyan; npx hardhat node" -WindowStyle Normal

Write-Host "Waiting 5 seconds for Hardhat node to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# --- STEP 5: Deploy the smart contract ---
Write-Host ""
Write-Host "[5/5] Deploying smart contract to local network..." -ForegroundColor Yellow
Set-Location $BlockchainDir
npx hardhat run scripts/deploy.js --network localhost
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Contract deployment failed. Is Hardhat node running?" -ForegroundColor Red
    Write-Host "Make sure the Hardhat node window opened successfully." -ForegroundColor Red
    exit 1
}
Write-Host "OK - Contract deployed" -ForegroundColor Green

# --- STEP 6: Launch FastAPI backend in new window ---
Write-Host ""
Write-Host "Starting FastAPI backend server..." -ForegroundColor Yellow
Set-Location $BackendDir
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BackendDir'; Write-Host 'FastAPI Backend Starting...' -ForegroundColor Cyan; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  ALL SERVERS STARTED!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Hardhat Node  : http://127.0.0.1:8545" -ForegroundColor White
Write-Host "  FastAPI + UI  : http://127.0.0.1:8000" -ForegroundColor White
Write-Host ""
Write-Host "  Open your browser at: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot
