# Setup Instructions

## Installing AWS SAM CLI on Windows

### Option 1: MSI Installer (Recommended)

1. Download the latest SAM CLI installer from:
   https://github.com/aws/aws-sam-cli/releases/latest
   
2. Look for the file: `AWSSAMCLISetup-*.msi`

3. Run the installer and follow the prompts

4. Close and reopen your PowerShell terminal

5. Verify installation:
   ```powershell
   sam --version
   ```

### Option 2: Chocolatey (If you have it installed)

```powershell
choco install aws-sam-cli
```

### Option 3: Manual pip install (If network allows)

```powershell
pip install aws-sam-cli
```

## After Installing SAM CLI

1. Verify AWS CLI is configured:
   ```powershell
   aws --version
   aws configure list
   ```

2. If AWS CLI is not installed, download from:
   https://aws.amazon.com/cli/

3. Configure your AWS credentials:
   ```powershell
   aws configure
   ```

## Next Steps

Once SAM CLI is installed:

1. Set up OpenRouter API key:
   ```powershell
   .\scripts\setup-secret.ps1 YOUR_OPENROUTER_API_KEY
   ```

2. Build and deploy:
   ```powershell
   cd infrastructure
   sam build
   sam deploy --guided
   ```

