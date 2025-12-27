# Rollback Checklist

## Rollback Triggers
- [ ] Smoke tests failing on production
- [ ] Error rate exceeds 5% for 10+ minutes
- [ ] Dashboard inaccessible for 5+ minutes
- [ ] Data corruption detected
- [ ] Critical security vulnerability

## Rollback Steps

1. **Stop Current Service**
   - Stop dashboard process
   - Note: systemctl stop agent-dashboard

2. **Backup Current State**
   - Backup database
   - Capture logs

3. **Restore Previous Version**
   - git checkout previous_version
   - pip install -e .

4. **Restore Database (if needed)**
   - Restore from backup

5. **Start Previous Version**
   - python src/web_server.py

## Post-Rollback Verification
- [ ] Dashboard accessible
- [ ] Smoke tests pass
- [ ] Error rate normal
- [ ] Data intact

## Communication
- [ ] Dev Team notified
- [ ] Product notified
- [ ] Support notified

*Template Version: 1.0.0*
