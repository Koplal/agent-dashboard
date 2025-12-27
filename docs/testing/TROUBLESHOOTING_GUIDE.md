# Troubleshooting Guide

## Top 20 Common Issues

### 1. Port 4200 Already in Use
**Solution:** Kill process or use --port flag

### 2. WebSocket Connection Failed
**Solution:** Check firewall, verify server running

### 3. Events Not Appearing in Dashboard
**Solution:** Verify dashboard URL, check server logs

### 4. Database Locked Error
**Solution:** Close other connections, restart server

### 5. Import Errors for Optional Dependencies
**Solution:** pip install networkx sentence-transformers rank-bm25

### 6. Memory Exhausted During Scale Tests
**Solution:** Reduce dataset size, increase swap

### 7. Slow Query Performance
**Solution:** Rebuild indexes, reduce top_k

### 8. Visualization Not Loading
**Solution:** Update Plotly, check browser

### 9. Test Fixtures Not Found
**Solution:** Run generate_test_data.py

### 10. Tokenizer Warnings
**Solution:** pip install transformers tokenizers

### 11. CORS Errors in Browser
**Solution:** Access from localhost

### 12. Hook Script Failures
**Solution:** Test manually with send_event.py

### 13. Session ID Not Persisting
**Solution:** Set CLAUDE_SESSION_ID env var

### 14. SSL/TLS Errors
**Solution:** pip install --upgrade certifi

### 15. Async Loop Already Running
**Solution:** Use nest_asyncio for Jupyter

### 16. Disk Space Exhausted
**Solution:** Clean old databases

### 17. Permission Denied Errors
**Solution:** chmod 755 ~/.claude

### 18. JSON Parse Errors
**Solution:** Check response is complete

### 19. Network Timeout Errors
**Solution:** Increase timeout values

### 20. Version Mismatch Errors
**Solution:** git pull origin main && pip install -e .

## Diagnostic Commands

404: Not Found

---
*Document Version: 1.0.0*
