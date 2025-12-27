# UI/UX Test Guide

## Overview

UI/UX tests (UI-001 through UI-005) verify dashboard visual presentation and interaction quality.

## Test Procedures

### UI-001: Responsive Layout - Mobile

**Steps:**
1. Open Chrome DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select iPhone SE (375x667)
4. Navigate dashboard

**Pass Criteria:** All content accessible, no horizontal scroll

---

### UI-002: Session Panel Interactions

**Steps:**
1. Click session to expand
2. Click again to collapse
3. Verify animation smoothness

**Pass Criteria:** Smooth animation, correct state toggle

---

### UI-003: Event Timeline Scrolling

**Steps:**
1. Open session with 100+ events
2. Scroll through timeline
3. Check for jank (use Performance tab)

**Pass Criteria:** 60 FPS scrolling

---

### UI-004: Agent Color Coding

**Steps:**
1. View events from different agent types
2. Verify color consistency
3. Check color contrast (accessibility tools)

**Pass Criteria:** Unique, consistent colors per agent

---

### UI-005: Dark Theme Accessibility

**Steps:**
1. Use Lighthouse accessibility audit
2. Check text contrast ratios
3. Verify focus indicators

**Pass Criteria:** WCAG AA compliance (4.5:1 contrast)

---

*Document Version: 1.0.0*
