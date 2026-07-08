# Maintainer sync

## DarkHerd -> this repo (after local improvements)

```bash
cd /path/to/cursor-dual-agent-loop
DARKHERD_PATH=/path/to/darkherd ./scripts/sync-from-darkherd.sh
git commit -am "Sync from darkherd"
```

## This repo -> DarkHerd (after public-repo improvements)

```bash
DARKHERD_PATH=/path/to/darkherd ./scripts/sync-to-darkherd.sh
```

## Community install

```bash
./scripts/install-into-repo.sh /path/to/their-project
```
