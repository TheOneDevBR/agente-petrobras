# Benchmark de Desempenho e Eficiência
**GPU:** NVIDIA GeForce GTX 1050 (3072 MiB VRAM, CUDA 13.0)
**Data:** 2026-06-10 (1ª rodada) / 2026-06-10 (2ª rodada — qwen3)

## Resultados — 1ª rodada

| Configuração | VRAM | Tempo | tok/s | tok/s/GB | Qualidade |
|---|---|---|---|---|---|
| **1.5B Windows GPU** | 1231 MB | 6.2s | 22.0 | 18.3 | OK |
| **7B Docker GPU** (layer split) | 2359 MB | 56.9s | 3.6 | 1.6 | Melhor |
| 7B Windows CPU | 0 MB | 76s | 0.85 | ∞ | OK, inviável |

## Resultados — 2ª rodada (qwen3)

| Modelo | Tamanho | VRAM (est.) | Tempo | tok/s | Qualidade |
|---|---|---|---|---|---|
| **qwen3:0.6b** | 522 MB | ~700 MB | 14.1s | 3.3 | OK (conciso) |
| **qwen3:1.7b** | 1.4 GB | ~1.5 GB | 30.1s | 1.2 | OK (mais detalhado) |
| **qwen2.5:1.5b** (referência) | 986 MB | 1231 MB | 6.4s | 6.1 | OK |

## Análise

- **1.5B GPU**: 1.2 GB VRAM, 22 tok/s — ideal para chat interativo (agente.py)
- **7B Docker GPU**: 2.4 GB VRAM, 3.6 tok/s — 6x mais lento que 1.5B, qualidade superior — ideal para coleta batch (coletor.py)
- **qwen3:0.6b**: 522 MB (mais leve), 3.3 tok/s — mais lento que qwen2.5:1.5b (que é mais rápido mesmo sendo maior)
- **qwen3:1.7b**: 1.4 GB, 1.2 tok/s — muito lento para uso interativo
- **7B CPU**: sem VRAM, 0.85 tok/s — inviável para uso real

## Recomendação

- `agente.py` (coach interativo): `qwen2.5:1.5b` (22 tok/s, responsivo)
- `coletor.py` (pesquisa batch): `qwen2.5:7b` via Docker (qualidade, tolera latência)
- `qwen3:0.6b` e `qwen3:1.7b`: inferiores ao `qwen2.5:1.5b` em velocidade — não substituem o default

## Como ativar o 7B via Docker

```powershell
docker start ollama-gpu
$env:AGENTE_LOCAL_MODEL="qwen2.5:7b"
python cli_python/coletor/coletor.py
```
