# CitizenTech RPA + IA — Triagem Inteligente de Zeladoria e Serviços Públicos

**Disciplina:** AI for Robotic Process Automation (RPA + IA) — Global Solution 2026.2  
**Integrantes do Grupo:**
- [PREENCHER NOME COMPLETO 1] — RM: [PREENCHER RM]
- [PREENCHER NOME COMPLETO 2] — RM: [PREENCHER RM]
- [PREENCHER NOME COMPLETO 3] — RM: [PREENCHER RM]

---

## 1. Descrição do Problema e Solução
Nas cidades brasileiras, prefeituras e órgãos públicos recebem milhares de solicitações cidadãs (buracos nas vias, falhas de iluminação pública, descarte irregular de lixo e vazamentos de esgoto) por canais não estruturados. A triagem manual gera atrasos no atendimento, perda de protocolos e demora na resposta ao morador.

Este protótipo automatiza o fluxo de ponta a ponta: ingere uma fila de solicitações cidadãs, valida e remove duplicidades, enriquece o endereço via API pública, classifica a categoria e a urgência com Inteligência Artificial (encaminhando casos ambíguos para revisão humana), persiste os protocolos em banco SQL e envia um comprovante automático ao cidadão.

---

## 2. Como Executar o Protótipo (Passo a Passo)

1. **Clonar/abrir a pasta do projeto** e criar um ambiente virtual Python (Python 3.10+):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate