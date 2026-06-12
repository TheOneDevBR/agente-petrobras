#!/bin/bash
# Inicia o servidor Ollama e faz pull dos modelos necessários

ollama serve &

sleep 5

ollama pull qwen2.5:1.5b
ollama pull qwen2.5:latest

wait
