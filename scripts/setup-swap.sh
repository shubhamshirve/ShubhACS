#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# setup-swap.sh — Create a 1 GB swap file on the host
# Run once as root before starting Docker containers:
#   sudo bash scripts/setup-swap.sh
# ─────────────────────────────────────────────────────────────
set -e

SWAP_FILE="/swapfile"
SWAP_SIZE_MB=1024

if swapon --show | grep -q "$SWAP_FILE"; then
    echo "✓ Swap already active at $SWAP_FILE"
    free -h
    exit 0
fi

echo "Creating ${SWAP_SIZE_MB} MB swap file at $SWAP_FILE ..."
fallocate -l "${SWAP_SIZE_MB}M" "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$SWAP_SIZE_MB" status=progress
chmod 600 "$SWAP_FILE"
mkswap "$SWAP_FILE"
swapon "$SWAP_FILE"

# Persist across reboots
if ! grep -q "$SWAP_FILE" /etc/fstab; then
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
fi

# Tune swappiness for better performance under low RAM
sysctl vm.swappiness=30
echo 'vm.swappiness=30' >> /etc/sysctl.conf 2>/dev/null || true

echo "✓ Swap file created and activated"
free -h
