# Backup Plan for Duplicate and Conflict Cleanup

**Created:** 2026-01-08  
**Purpose:** Document backup procedures before cleanup operations

---

## Overview

This document outlines the backup strategy for the duplicate and conflict cleanup operation. All files that will be removed or modified will be backed up to ensure safe rollback if issues occur.

---

## Backup Directory Structure

```
backups/
├── README.md                          # This file
├── backup_plan.md                     # Backup procedures
└── 2026-01-08_17-21-00/               # Timestamped backup directory
    ├── manifest.json                  # Backup manifest with file hashes
    ├── email_alerts.py.backup
    ├── keyword_rules_old_backup.py.backup
    ├── keyword_rules_v2.py.backup
    ├── keyword_rules.py.backup
    ├── utils/
    │   ├── email_alerts.py
    │   ├── duplicate_detector.py
    │   ├── semantic_duplicate_detector.py
    │   └── data_validator.py
    ├── config.yaml
    └── .env.example
```

---

## Files to Backup

### Category 1: Files to Remove (Backup Before Deletion)

| File | Size | Purpose |
|------|------|---------|
| `email_alerts.py.backup` | ~17 KB | Backup of email alerts utility |
| `keyword_rules_old_backup.py.backup` | ~3 KB | Old version of keyword rules |
| `keyword_rules_v2.py.backup` | ~3 KB | V2 backup of keyword rules |
| `keyword_rules.py.backup` | ~3 KB | Backup of current keyword rules |

**Total:** ~26 KB

### Category 2: Files to Modify (Backup Before Changes)

| File | Size | Purpose | Changes |
|------|------|---------|---------|
| `utils/email_alerts.py` | ~17 KB | Email alerts utility | Import updates |
| `utils/duplicate_detector.py` | ~5 KB | Duplicate detection | Import updates |
| `utils/semantic_duplicate_detector.py` | ~12 KB | Semantic duplicate detection | Import updates |
| `utils/data_validator.py` | ~8 KB | Data validator | Import updates |
| `config.yaml` | ~2 KB | Main configuration | Standardization |
| `.env.example` | ~1 KB | Environment template | Standardization |

**Total:** ~48 KB

---

## Backup Procedure

### Step 1: Create Timestamped Backup Directory

```bash
# Create backup directory with timestamp
BACKUP_DIR="backups/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$BACKUP_DIR"
echo "Backup directory created: $BACKUP_DIR"
```

### Step 2: Copy Files to Backup Directory

```bash
# Copy backup files (Category 1)
cp email_alerts.py.backup "$BACKUP_DIR/"
cp keyword_rules_old_backup.py.backup "$BACKUP_DIR/"
cp keyword_rules_v2.py.backup "$BACKUP_DIR/"
cp keyword_rules.py.backup "$BACKUP_DIR/"

# Copy files to be modified (Category 2)
mkdir -p "$BACKUP_DIR/utils"
cp utils/email_alerts.py "$BACKUP_DIR/utils/"
cp utils/duplicate_detector.py "$BACKUP_DIR/utils/"
cp utils/semantic_duplicate_detector.py "$BACKUP_DIR/utils/"
cp utils/data_validator.py "$BACKUP_DIR/utils/"
cp config.yaml "$BACKUP_DIR/"
cp .env.example "$BACKUP_DIR/"
```

### Step 3: Generate Backup Manifest

```bash
# Create manifest with file hashes
cd "$BACKUP_DIR"
cat > manifest.json << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_dir": "$BACKUP_DIR",
  "workspace_root": "$(cd ../.. && pwd)",
  "files": [
EOF

# Add file entries to manifest
for file in email_alerts.py.backup keyword_rules_old_backup.py.backup keyword_rules_v2.py.backup keyword_rules.py.backup; do
  if [ -f "$file" ]; then
    HASH=$(md5sum "$file" | cut -d' ' -f1)
    SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    echo "    {\"path\": \"$file\", \"size\": $SIZE, \"hash\": \"$HASH\", \"verified\": true}," >> manifest.json
  fi
done

for file in utils/email_alerts.py utils/duplicate_detector.py utils/semantic_duplicate_detector.py utils/data_validator.py config.yaml .env.example; do
  if [ -f "$file" ]; then
    HASH=$(md5sum "$file" | cut -d' ' -f1)
    SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    echo "    {\"path\": \"$file\", \"size\": $SIZE, \"hash\": \"$HASH\", \"verified\": true}," >> manifest.json
  fi
done

# Close manifest
sed -i '' '$ s/,$//' manifest.json
echo '  ]' >> manifest.json
echo '}' >> manifest.json

cd -
```

### Step 4: Verify Backup Integrity

```bash
# Verify all files were copied
echo "Verifying backup integrity..."
cd "$BACKUP_DIR"

# Count files
FILE_COUNT=$(find . -type f -not -name "manifest.json" | wc -l)
echo "Files backed up: $FILE_COUNT"

# Calculate total size
TOTAL_SIZE=$(du -sh . | cut -f1)
echo "Total backup size: $TOTAL_SIZE"

# Verify manifest
if [ -f "manifest.json" ]; then
  echo "✓ Manifest created successfully"
  echo "Manifest entries: $(jq '.files | length' manifest.json)"
else
  echo "✗ Manifest not found"
fi

cd -
```

---

## Verification Checklist

Before proceeding with cleanup, verify:

- [ ] Backup directory created successfully
- [ ] All 10 files copied to backup directory
- [ ] Manifest file created with file hashes
- [ ] File hashes calculated correctly
- [ ] Total backup size matches expectations (~74 KB)
- [ ] Backup directory is readable
- [ ] Manifest is valid JSON

---

## Rollback Procedure

If issues occur after cleanup:

### Step 1: Stop Running Processes

```bash
# Stop any running Python processes
pkill -f "python.*tenderscan"
pkill -f "python.*daily_runner"
pkill -f "flask"
```

### Step 2: Restore Files from Backup

```bash
# Set backup directory
BACKUP_DIR="backups/2026-01-08_17-21-00"

# Restore modified files
cp "$BACKUP_DIR/utils/email_alerts.py" utils/
cp "$BACKUP_DIR/utils/duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/semantic_duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/data_validator.py" utils/
cp "$BACKUP_DIR/config.yaml" .
cp "$BACKUP_DIR/.env.example" .

# Restore backup files (if they were deleted)
cp "$BACKUP_DIR/email_alerts.py.backup" .
cp "$BACKUP_DIR/keyword_rules_old_backup.py.backup" .
cp "$BACKUP_DIR/keyword_rules_v2.py.backup" .
cp "$BACKUP_DIR/keyword_rules.py.backup" .
```

### Step 3: Verify Restoration

```bash
# Verify file hashes match backup
cd "$BACKUP_DIR"

for file in utils/email_alerts.py utils/duplicate_detector.py utils/semantic_duplicate_detector.py utils/data_validator.py config.yaml .env.example; do
  BACKUP_HASH=$(jq -r ".files[] | select(.path==\"$file\") | .hash" manifest.json)
  RESTORED_HASH=$(md5sum "../../$file" | cut -d' ' -f1)
  
  if [ "$BACKUP_HASH" == "$RESTORED_HASH" ]; then
    echo "✓ $file restored successfully"
  else
    echo "✗ $file hash mismatch"
  fi
done

cd -
```

### Step 4: Test Functionality

```bash
# Run tests
python -m pytest tests/ -v

# Run daily scan
python daily_runner.py

# Verify email alerts
python utils/email_alerts.py
```

### Step 5: Document Issues

Create a rollback report:

```bash
cat > rollback_report_$(date +%Y%m%d_%H%M%S).md << EOF
# Rollback Report

**Date:** $(date)
**Reason:** [Describe issue that caused rollback]
**Backup Used:** $BACKUP_DIR

## Issues Encountered

1. [Issue 1]
2. [Issue 2]

## Root Cause Analysis

[Analysis of what went wrong]

## Lessons Learned

[What to avoid in future]
EOF
```

---

## Backup Retention Policy

- **Keep backups for:** 30 days after successful cleanup
- **Archive backups:** After 30 days, compress and move to archive
- **Delete old backups:** After 90 days, delete archived backups

```bash
# Compress old backup (after 30 days)
tar -czf backups/2026-01-08_17-21-00.tar.gz backups/2026-01-08_17-21-00/
rm -rf backups/2026-01-08_17-21-00/

# Delete old backup (after 90 days)
rm -f backups/2026-01-08_17-21-00.tar.gz
```

---

## Automated Backup Script

For automated backup creation, use the following commands:

```bash
#!/bin/bash
# backup.sh - Automated backup script

set -e

# Create timestamp
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="backups/$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo "Creating backup: $BACKUP_DIR"

# Copy files
cp email_alerts.py.backup "$BACKUP_DIR/" 2>/dev/null || true
cp keyword_rules_old_backup.py.backup "$BACKUP_DIR/" 2>/dev/null || true
cp keyword_rules_v2.py.backup "$BACKUP_DIR/" 2>/dev/null || true
cp keyword_rules.py.backup "$BACKUP_DIR/" 2>/dev/null || true

mkdir -p "$BACKUP_DIR/utils"
cp utils/email_alerts.py "$BACKUP_DIR/utils/"
cp utils/duplicate_detector.py "$BACKUP_DIR/utils/"
cp utils/semantic_duplicate_detector.py "$BACKUP_DIR/utils/"
cp utils/data_validator.py "$BACKUP_DIR/utils/"
cp config.yaml "$BACKUP_DIR/" 2>/dev/null || true
cp .env.example "$BACKUP_DIR/" 2>/dev/null || true

# Generate manifest
cd "$BACKUP_DIR"
# ... (manifest generation code from Step 3)
cd -

echo "Backup completed: $BACKUP_DIR"
```

---

## Summary

This backup plan ensures:

1. **All affected files are backed up** before cleanup
2. **File integrity is verified** using MD5 hashes
3. **Rollback is straightforward** if issues occur
4. **Backup history is maintained** for audit purposes
5. **Automated procedures** are available for consistency

**Total Files to Backup:** 10 files  
**Total Backup Size:** ~74 KB  
**Estimated Backup Time:** < 1 minute  
**Risk Level:** Low

---

## Next Steps

1. ✅ Review this backup plan
2. ✅ Execute backup procedure
3. ⏳ Verify backup integrity
4. ⏳ Proceed with cleanup operations
5. ⏳ Monitor for issues
6. ⏳ Clean up old backups after 30 days

---

**Document End**
