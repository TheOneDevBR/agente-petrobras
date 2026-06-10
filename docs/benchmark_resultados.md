# Benchmark de Desempenho e Eficiência
**GPU:** NVIDIA GeForce GTX 1050 (3072 MiB VRAM, CUDA 13.0)
**Data:** 2026-06-10

## Resultados

| Configuração | VRAM | Tempo | tok/s | tok/s/GB | Qualidade |
|---|---|---|---|---|---|
| **1.5B Windows GPU** | 1231 MB | 6.2s | 22.0 | 18.3 | OK |
| **7B Docker GPU** (layer split) | 2359 MB | 56.9s | 3.6 | 1.6 | Melhor |
| 7B Windows CPU | 0 MB | 76s | 0.85 | ∞ | OK, inviável |

## Análise

- **1.5B GPU**: 1.2 GB VRAM, 22 tok/s — ideal para chat interativo (agente.py)
- **7B Docker GPU**: 2.4 GB VRAM, 3.6 tok/s — 6x mais lento, mas qualidade superior — ideal para coleta batch (coletor.py)
- **7B CPU**: sem VRAM, 0.85 tok/s — 26x mais lento que 1.5B — inviável para uso real

## Recomendação

- `agente.py` (coach interativo): `qwen2.5:1.5b` (22 tok/s, responsivo)
- `coletor.py` (pesquisa batch): `qwen2.5:7b` via Docker (qualidade, tolera latência)

## Como ativar o 7B via Docker

```powershell
docker start ollama-gpu
$env:AGENTE_LOCAL_MODEL="qwen2.5:7b"
python cli_python/coletor/coletor.py
```
