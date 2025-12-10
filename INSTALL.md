# Installation Guide

Complete installation instructions for all supported environments.

## Quick Install (30 seconds)

```bash
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard
./scripts/install.sh
```

---

## Platform-Specific Instructions

<details>
<summary><b>Windows (Git Bash) - Click to expand</b></summary>

### Prerequisites

1. **Git Bash** (comes with Git for Windows)
   - Download: https://git-scm.com/download/win

2. **Python 3.9+**
   - Download: https://www.python.org/downloads/
   - **IMPORTANT:** Check "Add Python to PATH" during installation
   - **IMPORTANT:** Check "Install for all users" (recommended)

### Verify Prerequisites

Open Git Bash and run:
```bash
python --version   # Should show Python 3.9+
pip --version      # Should show pip
```

### Installation

```bash
# Clone repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Run installer
./scripts/install.sh
```

### Start Dashboard

```bash
agent-dashboard --web
# Open http://localhost:4200 in browser
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `python3: command not found` | Windows uses `python` | The installer handles this automatically |
| `\r: command not found` | Windows line endings | `sed -i 's/\r$//' scripts/install.sh` |
| `Permission denied` | Script not executable | `chmod +x scripts/install.sh` |
| Firewall prompt | Windows Defender | Click "Allow access" |

### VS Code Users

1. Open VS Code in the `agent-dashboard` folder
2. Open terminal: `Ctrl+``
3. **Change terminal to Git Bash:**
   - Click dropdown arrow next to `+` in terminal
   - Select "Git Bash"
4. Run: `./scripts/install.sh`

</details>

<details>
<summary><b>macOS (Homebrew) - Click to expand</b></summary>

### Prerequisites

1. **Homebrew**
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Python 3.9+**
   ```bash
   brew install python@3.11
   ```

3. **Xcode Command Line Tools** (for some pip packages)
   ```bash
   xcode-select --install
   ```

### Verify Prerequisites

```bash
python3 --version  # Should show Python 3.9+
pip3 --version     # Should show pip
```

### Installation

```bash
# Clone repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Make executable (first time only)
chmod +x scripts/install.sh

# Run installer
./scripts/install.sh
```

### Start Dashboard

```bash
agent-dashboard --web
# Open http://localhost:4200 in browser
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| "cannot be opened because the developer cannot be verified" | Gatekeeper | Right-click -> Open, or: `xattr -d com.apple.quarantine scripts/install.sh` |
| `pip3: command not found` | Homebrew not in PATH | Add to ~/.zshrc: `export PATH="/opt/homebrew/bin:$PATH"` |
| Build errors during pip install | Missing Xcode tools | `xcode-select --install` |

### Apple Silicon (M1/M2/M3) Notes

Homebrew installs to `/opt/homebrew` on Apple Silicon (not `/usr/local`).

If you have issues, ensure your PATH is correct:
```bash
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

</details>

<details>
<summary><b>Linux (Ubuntu/Debian) - Click to expand</b></summary>

### Prerequisites

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl
```

### Verify Prerequisites

```bash
python3 --version  # Should show Python 3.9+
pip3 --version     # Should show pip
```

### Installation

```bash
# Clone repository
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Run installer
./scripts/install.sh
```

### Start Dashboard

```bash
agent-dashboard --web
# Open http://localhost:4200 in browser
```

### Headless Server (No Desktop)

To access the dashboard from your local machine:

```bash
# On your LOCAL machine, create SSH tunnel:
ssh -L 4200:localhost:4200 user@your-server

# On the SERVER, start dashboard:
agent-dashboard --web

# On your LOCAL machine, open browser:
# http://localhost:4200
```

</details>

<details>
<summary><b>Linux (Fedora/RHEL) - Click to expand</b></summary>

### Prerequisites

```bash
sudo dnf install python3 python3-pip git curl
```

### Installation

```bash
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard
./scripts/install.sh
```

</details>

<details>
<summary><b>Linux (Arch) - Click to expand</b></summary>

### Prerequisites

```bash
sudo pacman -S python python-pip git curl
```

### Installation

```bash
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard
./scripts/install.sh
```

</details>

<details>
<summary><b>Windows (WSL2) - Click to expand</b></summary>

### Prerequisites

1. **Enable WSL2**
   ```powershell
   # In PowerShell (Admin)
   wsl --install -d Ubuntu
   ```

2. **Open Ubuntu terminal** and install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git curl
   ```

### Installation

```bash
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard
./scripts/install.sh
```

### Access from Windows Browser

The dashboard URL `http://localhost:4200` works directly from Windows browsers when running in WSL2.

</details>

<details>
<summary><b>Docker - Click to expand</b></summary>

### Quick Start

```bash
# Clone and start
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard
./scripts/docker-start.sh

# Or with docker-compose directly
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker Run

```bash
# Build image
docker build -t agent-dashboard .

# Run container
docker run -d \
  --name agent-dashboard \
  -p 4200:4200 \
  -v agent-dashboard-data:/home/appuser/.claude \
  agent-dashboard

# View logs
docker logs -f agent-dashboard

# Stop
docker stop agent-dashboard
docker rm agent-dashboard
```

### Docker Compose with Custom Port

Create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  dashboard:
    ports:
      - "8080:4200"  # Access on port 8080 instead
```

</details>

---

## Python Environment Managers

<details>
<summary><b>pyenv - Click to expand</b></summary>

### Installation

```bash
# Install Python 3.11 via pyenv
pyenv install 3.11
pyenv local 3.11  # or: pyenv global 3.11

# Verify
python --version  # Should show 3.11.x

# Install dashboard
./scripts/install.sh
```

</details>

<details>
<summary><b>Conda/Miniconda - Click to expand</b></summary>

### Create Dedicated Environment (Recommended)

```bash
# Create environment
conda create -n claude-dashboard python=3.11 -y
conda activate claude-dashboard

# Install dashboard
./scripts/install.sh
```

### Using Base Environment

```bash
conda activate base
./scripts/install.sh
```

**Note:** Installing to `base` is not recommended as it may conflict with other packages.

</details>

<details>
<summary><b>Virtual Environment (venv) - Click to expand</b></summary>

### Create and Activate

```bash
# Create venv
python3 -m venv ~/.claude-venv

# Activate (Linux/macOS)
source ~/.claude-venv/bin/activate

# Activate (Windows Git Bash)
source ~/.claude-venv/Scripts/activate

# Install dashboard
./scripts/install.sh

# Deactivate when done
deactivate
```

</details>

---

## Verification

After installation, verify everything works:

```bash
# Check installation
agent-dashboard doctor

# Start dashboard
agent-dashboard --web

# Open http://localhost:4200 in browser
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed error solutions.

### Quick Fixes

| Issue | Solution |
|-------|----------|
| `agent-dashboard: command not found` | Run: `source ~/.bashrc` or open new terminal |
| Dependencies missing | Run: `pip install rich aiohttp tiktoken` |
| Port 4200 in use | Use different port: `agent-dashboard --web --port 4201` |
| Permission denied | Run: `chmod +x scripts/install.sh` |

---

## Next Steps

After installation:

1. **Start the dashboard:** `agent-dashboard --web`
2. **Use an agent:** `export AGENT_NAME=orchestrator && claude`
3. **Read the docs:** [README.md](README.md)
