#!/bin/sh
# ollama-pull-private.sh
# ─────────────────────────────────────────────────────────────────────────────
# Autonomyx Model Gateway — Private Node Model Pull Script
#
# Detects available RAM and pulls appropriate models.
# Edit TIER below to override auto-detection.
# ─────────────────────────────────────────────────────────────────────────────

set -e

# ── Auto-detect RAM tier ──────────────────────────────────────────────────────
TOTAL_RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)

if [ -n "$FORCE_TIER" ]; then
  TIER=$FORCE_TIER
elif [ "$TOTAL_RAM_GB" -ge 80 ]; then
  TIER=96
elif [ "$TOTAL_RAM_GB" -ge 56 ]; then
  TIER=64
elif [ "$TOTAL_RAM_GB" -ge 24 ]; then
  TIER=32
else
  TIER=16
fi

echo "============================================"
echo " Autonomyx Private Node — Model Pull"
echo " Detected RAM: ${TOTAL_RAM_GB}GB → Tier: ${TIER}GB"
echo "============================================"
echo ""

case "$TIER" in

  16)
    echo "Tier 16GB: 7B/8B models only"
    echo "  Suitable for: chat, summarise, extract, simple code"
    echo ""
    ollama pull llama3.1:8b
    ollama pull mistral:7b-instruct
    ollama pull qwen2.5-coder:7b
    echo ""
    echo "Models ready:"
    echo "  llama3.1:8b       → chat, extract    (40-60 tok/s)"
    echo "  mistral:7b        → summarise         (40-60 tok/s)"
    echo "  qwen2.5-coder:7b  → code              (40-60 tok/s)"
    ;;

  32)
    echo "Tier 32GB: 14B always-on + 7B warm slot"
    echo "  Suitable for: code review, extract, reasoning, chat"
    echo ""
    echo "[1/4] Pulling Qwen2.5-14B (always-on, extract + structured output)..."
    ollama pull qwen2.5:14b
    echo "[2/4] Pulling Qwen2.5-Coder-14B (always-on, code)..."
    ollama pull qwen2.5-coder:14b
    echo "[3/4] Pulling Llama3.1-8B (warm slot, chat)..."
    ollama pull llama3.1:8b
    echo "[4/4] Pulling Mistral-7B (warm slot, summarise)..."
    ollama pull mistral:7b-instruct
    echo ""
    echo "Warming always-on models..."
    ollama run qwen2.5:14b "Ready." --keepalive 24h &
    ollama run qwen2.5-coder:14b "Ready." --keepalive 24h &
    wait
    echo ""
    echo "Models ready:"
    echo "  qwen2.5:14b        → extract, structured output (always-on, 25-40 tok/s)"
    echo "  qwen2.5-coder:14b  → code                       (always-on, 25-40 tok/s)"
    echo "  llama3.1:8b        → chat                       (warm slot, 40-60 tok/s)"
    echo "  mistral:7b         → summarise                  (warm slot, 40-60 tok/s)"
    ;;

  64)
    echo "Tier 64GB: 32B always-on (code or reason) + 8B warm slot"
    echo "  Choose your primary workload:"
    echo "  CODE_FOCUS=1  → Qwen2.5-Coder-32B always-on"
    echo "  REASON_FOCUS=1 → Qwen3-30B-A3B always-on"
    echo "  Default: both if RAM allows"
    echo ""
    if [ "$CODE_FOCUS" = "1" ]; then
      echo "Code-focused deployment"
      ollama pull qwen2.5-coder:32b
      ollama pull llama3.1:8b
      ollama pull mistral:7b-instruct
      ollama run qwen2.5-coder:32b "Ready." --keepalive 24h &
      wait
    elif [ "$REASON_FOCUS" = "1" ]; then
      echo "Reasoning-focused deployment"
      ollama pull qwen3:30b-a3b
      ollama pull llama3.1:8b
      ollama pull mistral:7b-instruct
      ollama run qwen3:30b-a3b "Ready." --keepalive 24h &
      wait
    else
      echo "Balanced: Qwen3-30B (reason) + 8B warm slots"
      ollama pull qwen3:30b-a3b
      ollama pull qwen2.5-coder:7b
      ollama pull llama3.1:8b
      ollama run qwen3:30b-a3b "Ready." --keepalive 24h &
      wait
    fi
    echo ""
    echo "Models ready. Run: docker exec private-ollama ollama ps"
    ;;

  96)
    echo "Tier 96GB: Full stack — same as Autonomyx primary node"
    echo ""
    echo "[1/6] Qwen3-30B-A3B (reason + agent, always-on)..."
    ollama pull qwen3:30b-a3b
    echo "[2/6] Qwen2.5-Coder-32B (code, always-on)..."
    ollama pull qwen2.5-coder:32b
    echo "[3/6] Qwen2.5-14B (extract, always-on)..."
    ollama pull qwen2.5:14b
    echo "[4/6] Llama3.1-8B (chat warm slot)..."
    ollama pull llama3.1:8b
    echo "[5/6] Llama3.2-Vision-11B (vision warm slot)..."
    ollama pull llama3.2-vision:11b
    echo "[6/6] Gemma3-9B (long context warm slot)..."
    ollama pull gemma3:9b
    echo ""
    echo "Warming always-on models..."
    ollama run qwen3:30b-a3b "Ready." --keepalive 24h &
    ollama run qwen2.5-coder:32b "Ready." --keepalive 24h &
    ollama run qwen2.5:14b "Ready." --keepalive 24h &
    wait
    echo ""
    echo "Full stack ready. Peak RAM: ~84GB / 96GB"
    ;;

  *)
    echo "Unknown tier. Using 8B only."
    ollama pull llama3.1:8b
    ;;

esac

echo ""
echo "[+] Pulling nomic-embed-text (RAG embeddings, 274MB)..."
ollama pull nomic-embed-text
echo "    Done."
echo ""
echo "============================================"
echo " Pull complete."
echo " Monitor: docker exec private-ollama ollama ps"
echo " Add models: docker exec private-ollama ollama pull <model>"
echo "============================================"
