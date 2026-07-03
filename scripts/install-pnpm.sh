#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# install-pnpm.sh — Install pnpm for local development
# Replaces yarn for faster installs and lower disk usage
# ─────────────────────────────────────────────────────────────
set -e

echo "Installing pnpm..."
npm install -g pnpm

echo "Installing frontend dependencies with pnpm..."
cd /app/frontend
pnpm import 2>/dev/null || true   # Convert yarn.lock → pnpm-lock.yaml
pnpm install

echo ""
echo "✓ pnpm installed. Use 'pnpm start' instead of 'yarn start'."
echo "  Update supervisor config to use: pnpm start"
