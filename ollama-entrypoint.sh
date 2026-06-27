#!/bin/bash
# Inicia o servidor Ollama e faz pull dos modelos necessários em background
set -e

# Inicia servidor em background
ollama serve &

# Aguarda o servidor ficar pronto (máx 60s)
for i in $(seq 1 30); do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama server ready"
    break
  fi
  echo "Waiting for Ollama server... ($i)"
  sleep 2
done

# Pull modelos em background (não bloqueia healthcheck)
for model in qwen2.5:1.5b qwen2.5:latest; do
  if ! ollama list 2>/dev/null | grep -q "$model"; then
    echo "Pulling $model in background..."
    (ollama pull "$model" 2>&1 | tail -1) &
  else
    echo "$model already available"
  fi
done

wait
