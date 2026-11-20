# Relatório de Execução e Evidências de Validação — CitizenTech RPA + IA
**Data/Hora da Execução:** 20/11/2026 00:13:35

## 1. Resumo Operacional do Fluxo
- **Total de registros lidos (CSV):** 15
- **Duplicidades barradas (Idempotência):** 1
- **Registros inválidos descartados com log:** 2
- **Protocolos gravados no Banco SQLite (`citizentech_rpa.db`):** 12
- **Encaminhados para Revisão Humana (baixa confiança IA):** 7
- **Fallbacks de API externa tratados sem quebra:** 2

## 2. Métricas da Inteligência Artificial (Amostra Rotulada)
- **Amostra válida avaliada:** 12 solicitações
- **Acertos:** 6 / 12
- **Acurácia observada:** 50.0%

| ID | Categoria Esperada | Categoria Prevista (IA) | Confiança | Status |
| :--- | :--- | :--- | :---: | :---: |
| SOL-001 | Infraestrutura | Revisao Humana | 0.46 | Erro |
| SOL-002 | Iluminacao Publica | Revisao Humana | 0.47 | Erro |
| SOL-003 | Limpeza Urbana | Limpeza Urbana | 0.57 | Acerto |
| SOL-004 | Saude e Saneamento | Saude e Saneamento | 0.66 | Acerto |
| SOL-005 | Infraestrutura | Revisao Humana | 0.55 | Erro |
| SOL-006 | Iluminacao Publica | Iluminacao Publica | 0.58 | Acerto |
| SOL-007 | Limpeza Urbana | Limpeza Urbana | 0.61 | Acerto |
| SOL-008 | Saude e Saneamento | Saude e Saneamento | 0.60 | Acerto |
| SOL-009 | Infraestrutura | Revisao Humana | 0.44 | Erro |
| SOL-010 | Iluminacao Publica | Revisao Humana | 0.52 | Erro |
| SOL-011 | Limpeza Urbana | Revisao Humana | 0.45 | Erro |
| SOL-012 | Revisao Humana | Revisao Humana | 0.31 | Acerto |

## 3. Evidências de Falhas Tratadas com Segurança
- [Resiliência] Tratamento validado: 'arquivo_que_nao_existe.csv' ausente capturado sem interromper o robô.
- [API Fallback] SOL-005 (CEP 40020000) tratado via fallback: CEP_NAO_ENCONTRADO
- [API Fallback] SOL-011 (CEP 99999999) tratado via fallback: CEP_NAO_ENCONTRADO
- [Dado Inválido] SOL-013 descartado com segurança -> Motivo: CEP inválido (123)
- [Dado Inválido] SOL-014 descartado com segurança -> Motivo: Relato ausente ou curto demais (< 10 caracteres)

> Logs detalhados salvos em: `logs/execucao_rpa.log`
