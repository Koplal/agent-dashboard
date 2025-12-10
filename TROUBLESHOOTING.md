# Troubleshooting Guide

Solutions for common issues organized by error message.

---

## Quick Diagnostics

Run this first to identify issues:
```bash
agent-dashboard doctor
```

---

## Error Index

### Installation Errors

<details>
<summary><b><code>python3: command not found</code></b></summary>

**Platforms:** Windows Git Bash

**Cause:** Windows typically uses `python` instead of `python3`.

**Solutions:**

1. **Automatic (Recommended):** The installer now auto-detects `python` on Windows. Re-run:
   ```bash
   ./scripts/install.sh
   ```

2. **Manual alias:**
   ```bash
   # Add to ~/.bashrc
   alias python3=python
   alias pip3=pip
   ```

3. **Reinstall Python:**
   - Download from https://python.org
   - Check "Add Python to PATH" during installation
   - Restart Git Bash

</details>

<details>
<summary><b><code>\r: command not found</code></b></summary>

**Platforms:** Windows

**Cause:** The script has Windows line endings (CRLF) instead of Unix (LF).

**Solutions:**

1. **Convert line endings:**
   ```bash
   sed -i 's/\r$//' scripts/install.sh
   ```

2. **Configure Git:**
   ```bash
   git config --global core.autocrlf false
   git checkout -- scripts/install.sh
   ```

3. **Re-clone with correct settings:**
   ```bash
   rm -rf agent-dashboard
   git config --global core.autocrlf false
   git clone https://github.com/Koplal/agent-dashboard.git
   ```

</details>

<details>
<summary><b><code>Permission denied</code></b></summary>

**Cause:** Script not marked as executable.

**Solution:**
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

</details>

<details>
<summary><b><code>ModuleNotFoundError: No module named 'rich'</code></b></summary>

**Cause:** Python dependencies not installed.

**Solution:**
```bash
pip install rich aiohttp tiktoken
# Or:
pip3 install rich aiohttp tiktoken
# Or:
python -m pip install rich aiohttp tiktoken
```

</details>

<details>
<summary><b><code>pip: command not found</code></b></summary>

**Cause:** pip not installed or not in PATH.

**Solutions:**

1. **Install pip:**
   ```bash
   python -m ensurepip --upgrade
   ```

2. **Use python -m pip:**
   ```bash
   python -m pip install rich aiohttp tiktoken
   ```

3. **Install via package manager:**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3-pip

   # Fedora
   sudo dnf install python3-pip

   # macOS
   brew install python3
   ```

</details>

---

### Runtime Errors

<details>
<summary><b><code>agent-dashboard: command not found</code></b></summary>

**Cause:** `~/.local/bin` not in PATH.

**Solutions:**

1. **Reload shell config:**
   ```bash
   source ~/.bashrc   # Bash
   source ~/.zshrc    # Zsh
   ```

2. **Open new terminal window**

3. **Run directly:**
   ```bash
   ~/.local/bin/agent-dashboard --web
   ```

4. **Add to PATH manually:**
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

</details>

<details>
<summary><b><code>Address already in use</code> (Port 4200)</b></summary>

**Cause:** Another process is using port 4200.

**Solutions:**

1. **Use different port:**
   ```bash
   agent-dashboard --web --port 4201
   ```

2. **Find and kill process using port:**
   ```bash
   # Linux/macOS
   lsof -i :4200
   kill <PID>

   # Windows
   netstat -ano | findstr :4200
   taskkill /PID <PID> /F
   ```

</details>

<details>
<summary><b>Events not appearing in dashboard</b></summary>

**Causes:**
1. Dashboard not running
2. Hooks not configured
3. Network issue

**Solutions:**

1. **Verify dashboard is running:**
   ```bash
   curl http://localhost:4200/health
   ```

2. **Check hooks configuration:**
   ```bash
   cat ~/.claude/settings.json | grep run_hook
   ```

3. **Send test event:**
   ```bash
   agent-dashboard test
   ```

4. **Check hook script permissions:**
   ```bash
   ls -la ~/.claude/dashboard/hooks/
   chmod +x ~/.claude/dashboard/hooks/run_hook.sh
   ```

5. **Reinstall hooks:**
   ```bash
   ./scripts/install.sh
   # Answer 'y' when prompted for hook configuration
   ```

</details>

<details>
<summary><b><code>Connection refused</code> when sending events</b></summary>

**Cause:** Dashboard server not running.

**Solution:**
```bash
# Start the dashboard in one terminal
agent-dashboard --web

# Then send test event in another terminal
agent-dashboard test
```

</details>

---

### Platform-Specific Errors

<details>
<summary><b>macOS: "cannot be opened because the developer cannot be verified"</b></summary>

**Cause:** macOS Gatekeeper blocking unsigned scripts.

**Solutions:**

1. **Right-click method:**
   - Right-click `install.sh` in Finder
   - Click "Open"
   - Click "Open" again in dialog

2. **Remove quarantine attribute:**
   ```bash
   xattr -d com.apple.quarantine scripts/install.sh
   ```

3. **Allow in System Preferences:**
   - System Preferences -> Security & Privacy
   - Click "Allow Anyway"

</details>

<details>
<summary><b>macOS: Homebrew Python not found</b></summary>

**Cause:** Homebrew path not in shell PATH.

**Solutions:**

For Apple Silicon (M1/M2/M3):
```bash
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

For Intel Macs:
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

</details>

<details>
<summary><b>Windows Firewall prompt when starting dashboard</b></summary>

**Cause:** Windows Defender Firewall detecting network listener.

**Solution:** Click "Allow access" when prompted. This is normal behavior for web servers.

If you blocked it accidentally:
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find Python and enable both Private and Public

</details>

<details>
<summary><b>WSL2: Dashboard not accessible from Windows browser</b></summary>

**Cause:** Network configuration issue.

**Solutions:**

1. **Use localhost** (should work automatically):
   ```
   http://localhost:4200
   ```

2. **Use WSL IP:**
   ```bash
   # In WSL, get IP:
   ip addr show eth0 | grep inet
   # Use that IP in Windows browser
   ```

3. **Restart WSL:**
   ```powershell
   wsl --shutdown
   wsl
   ```

</details>

---

### Docker Errors

<details>
<summary><b>Docker build fails</b></summary>

**Solutions:**

1. **Clear Docker cache:**
   ```bash
   docker-compose build --no-cache
   ```

2. **Check Docker is running:**
   ```bash
   docker info
   ```

3. **Check disk space:**
   ```bash
   docker system df
   docker system prune
   ```

</details>

<details>
<summary><b>Container exits immediately</b></summary>

**Solution:** Check logs for errors:
```bash
docker-compose logs dashboard
```

</details>

---

## Diagnostic Commands

```bash
# Full system check
agent-dashboard doctor

# Check Python
python3 --version
python --version

# Check dependencies
python3 -c "import rich; print(rich.__version__)"
python3 -c "import aiohttp; print(aiohttp.__version__)"
python3 -c "import tiktoken; print('ok')"

# Check installation
ls -la ~/.claude/dashboard/
ls -la ~/.claude/agents/

# Check PATH
echo $PATH | tr ':' '\n' | grep local

# Test dashboard connectivity
curl http://localhost:4200/health

# Check port usage
lsof -i :4200  # macOS/Linux
netstat -ano | findstr :4200  # Windows

# View recent events
agent-dashboard logs -n 20
```

---

## Complete Reset

If all else fails, do a clean reinstall:

```bash
# Uninstall
./scripts/uninstall.sh
# Or: agent-dashboard uninstall

# Re-clone
cd ..
rm -rf agent-dashboard
git clone https://github.com/Koplal/agent-dashboard.git
cd agent-dashboard

# Reinstall
./scripts/install.sh
```

---

## Getting Help

If you're still stuck:

1. **Run diagnostics:** `agent-dashboard doctor`
2. **Check logs:** `agent-dashboard logs`
3. **Open an issue:** https://github.com/Koplal/agent-dashboard/issues

Include in your issue:
- Output of `agent-dashboard doctor`
- Your OS and version
- Python version (`python --version`)
- Full error message
