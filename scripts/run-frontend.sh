#!/bin/bash
# Run the Next.js frontend (from repo root).
# Requires: npm install in frontend/
set -e
cd "$(dirname "$0")/../frontend"
npm run dev
