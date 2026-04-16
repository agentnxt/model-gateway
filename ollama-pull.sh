#!/bin/sh
# ollama-pull.sh — Autonomyx Model Gateway, Operator Primary Node (96GB)
# Pulls the full Option C stack. Takes 60-90 minutes on first run.
# Run inside the Ollama container: docker exec autonomyx-ollama sh /ollama-pull.sh

set -e

echo "============================================"
echo " Autonomyx Model Gateway — Operator Stack"
echo " Pulling full 96GB model suite"
echo "============================================"
echo ""

echo "[1/7] Qwen3-30B-A3B (reason + agent, always-on, 19GB)..."
ollama pull qwen3:30b-a3b

echo "[2/7] Qwen2.5-Coder-32B (code, always-on, 22GB)..."
ollama pull qwen2.5-coder:32b

echo "[3/7] Qwen2.5-14B (extract + structured output, always-on, 9GB)..."
ollama pull qwen2.5:14b

echo "[4/7] Llama3.1-8B (chat overflow, warm slot, 6GB)..."
ollama pull llama3.1:8b

echo "[5/7] Llama3.2-Vision-11B (vision, warm slot, 9GB)..."
ollama pull llama3.2-vision:11b

echo "[6/7] Gemma3-9B (long context, warm slot, 6GB)..."
ollama pull gemma3:9b

echo "[7/7] nomic-embed-text (RAG embeddings, always-on, 274MB)..."
ollama pull nomic-embed-text

echo ""
echo "Warming always-on models (pinning to RAM for 24h)..."
ollama run qwen3:30b-a3b    "Ready." --keepalive 24h &
ollama run qwen2.5-coder:32b "Ready." --keepalive 24h &
ollama run qwen2.5:14b       "Ready." --keepalive 24h &
wait

echo ""
echo "============================================"
echo " Pull complete. RAM usage:"
echo "   qwen3:30b-a3b     19GB  always-on"
echo "   qwen2.5-coder:32b 22GB  always-on"
echo "   qwen2.5:14b        9GB  always-on"
echo "   llama3.1:8b        6GB  warm slot"
echo "   llama3.2-vision   9GB  warm slot"
echo "   gemma3:9b          6GB  warm slot"
echo "   nomic-embed-text 274MB  always-on"
echo "   Peak total:       ~84GB / 96GB"
echo ""
echo " Monitor: docker exec autonomyx-ollama ollama ps"
echo "============================================"
