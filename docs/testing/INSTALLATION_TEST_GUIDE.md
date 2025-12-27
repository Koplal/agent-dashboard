# Installation Test Guide

## Overview

Installation tests (IN-001 through IN-004) verify cross-platform installation success.

## Test Environments

| Platform | Version | Status |
|----------|---------|--------|
| Windows | 10/11 | |
| macOS | 12+ | |
| Ubuntu | 22.04 | |
| WSL2 | Ubuntu | |

## Test Procedures

### IN-001: Windows Installation

**Prerequisites:**
- Clean Windows 10/11 VM
- Python 3.10+ installed
- Git installed

**Steps:**
1. Clone repository
2. Run: python scripts/install.py
3. Start: python src/web_server.py
4. Open: http://localhost:4200

**Pass Criteria:** Dashboard starts, events can be sent

---

### IN-002: macOS Installation

**Steps:**
1. Clone repository
2. Run: python scripts/install.py
3. Start dashboard
4. Verify functionality

---

### IN-003: Linux Installation

**Steps:**
1. Clone on Ubuntu 22.04
2. Run installer
3. Verify dashboard

---

### IN-004: WSL2 Installation

**Steps:**
1. Clone in WSL2
2. Run installer
3. Access from Windows browser

---

*Document Version: 1.0.0*
