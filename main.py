import logging
import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from ia_triagem import ClassificadorCidadaoIA
from servicos_rpa import NotificadorEmailRPA, RepositorioProtocolosSQL, ServicoViaCEP


def configurar_logs() -> str:
    os.makedirs("logs", exist_ok=True)
    caminho_log = os.path.join("logs", "execucao_rpa.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(caminho_log, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return caminho_log


def validar_registro(linha: pd.Series) -> tuple[bool, str]:
    id_sol = str(linha.get("id_solicitacao", "")).strip()
    relato = str(linha.get("relato", "")).strip()
    cep = "".join(filter(str.isdigit, str(linha.get("cep", ""))))
    email = str(linha.get("email_cidadao", "")).strip()

    if not id_sol or id_sol == "nan":
        return False, "ID da solicitação ausente"
    if not relato or relato == "nan" or len(relato) < 10:
        return False, "Relato ausente ou curto demais (< 10 caracteres)"
    if len(cep) != 8:
        return False, f"CEP inválido ({linha.get('cep')})"
    if "@" not in email:
        return False, f"E-mail inválido ({email})"
    return True, "OK"


def testar_resiliencia_arquivo_ausente() -> str:
    arquivo_inexistente = "arquivo_que_nao_existe.csv"
    try:
        pd.read_csv(arquivo_inexistente)
        return "Falha não ocorreu"
    except FileNotFoundError:
        msg = f"[Resiliência] Tratamento validado: '{arquivo_inexistente}' ausente capturado sem interromper o robô."
        logging.warning(msg)
        return msg


def executar_pipeline() -> None:
    load_dotenv()
    caminho_log = configurar_logs()
    logging.info("=== INICIANDO ROBÔ CITIZENTECH RPA + IA ===")

    # 1. Demonstração explícita de tratamento de arquivo ausente
    evidencia_arquivo_ausente = testar_resiliencia_arquivo_ausente()

    arquivo_entrada = os.getenv("ARQUIVO_ENTRADA", "dados_cidadaos.csv")
    banco_sqlite = os.getenv("BANCO_SQLITE", "citizentech_rpa.db")
    limiar_ia = float(os.getenv("LIMIAR_CONFIANCA_IA", "0.55"))
    modo_sim_email = os.getenv("MODO_SIMULACAO_EMAIL", "true").lower() == "true"

    # Reinicia banco de demonstração para execução limpa reproduzível
    if os.path.exists(banco_sqlite):
        os.remove(banco_sqlite)

    # Inicializa componentes
    ia = ClassificadorCidadaoIA(limiar_confianca=limiar_ia)
    api_cep = ServicoViaCEP(timeout=4, max_tentativas=2)
    repo_sql = RepositorioProtocolosSQL(banco_sqlite)
    notificador = NotificadorEmailRPA(modo_simulacao=modo_sim_email)

    # 2. Tema Pandas: Ingestão e higienização inicial
    try:
        df = pd.read_csv(arquivo_entrada, dtype={"cep": str})
    except FileNotFoundError:
        logging.critical(f"Arquivo principal '{arquivo_entrada}' não encontrado. Encerrando com segurança.")
        return

    total_lidos = len(df)
    logging.info(f"[Pandas] Total de linhas lidas de '{arquivo_entrada}': {total_lidos}")

    # Deduplicação em lote via Pandas (Idempotência na entrada)
    df_sem_duplicatas = df.drop_duplicates(subset=["id_solicitacao"], keep="first").copy()
    duplicados_removidos = total_lidos - len(df_sem_duplicatas)
    if duplicados_removidos > 0:
        logging.warning(f"[Idempotência] {duplicados_removidos} registro(s) duplicado(s) ignorado(s) pelo Pandas.")

    estatisticas = {
        "lidos": total_lidos,
        "duplicados_ignorados": duplicados_removidos,
        "invalidos_descartados": 0,
        "processados_sucesso": 0,
        "revisao_humana": 0,
        "fallbacks_api": 0,
        "acertos_ia": 0,
        "avaliados_ia": 0,
    }
    detalhes_avaliacao = []
    falhas_tratadas = [evidencia_arquivo_ausente]

    # 3. Processamento linha a linha
    for _, linha in df_sem_duplicatas.iterrows():
        id_sol = str(linha.get("id_solicitacao", "SEM_ID")).strip()

        # Idempotência no Banco SQL
        if repo_sql.ja_processado(id_sol):
            logging.info(f"[SQL Idempotência] {id_sol} já registrado anteriormente. Pulando.")
            continue

        # Validação de integridade dos dados
        valido, motivo = validar_registro(linha)
        if not valido:
            estatisticas["invalidos_descartados"] += 1
            msg_erro = f"[Dado Inválido] {id_sol} descartado com segurança -> Motivo: {motivo}"
            logging.warning(msg_erro)
            falhas_tratadas.append(msg_erro)
            continue

        # Enriquecimento via API ViaCEP
        cep_limpo = "".join(filter(str.isdigit, str(linha["cep"])))
        info_endereco = api_cep.consultar_cep(cep_limpo)
        if info_endereco["status_api"] != "OK":
            estatisticas["fallbacks_api"] += 1
            falhas_tratadas.append(
                f"[API Fallback] {id_sol} (CEP {cep_limpo}) tratado via fallback: {info_endereco['status_api']}"
            )

        endereco_completo = f"{info_endereco['logradouro']} - {info_endereco['bairro']} ({info_endereco['cidade_uf']})"

        # Classificação Inteligente (IA)
        relato = str(linha["relato"]).strip()
        resultado_ia = ia.classificar(relato)
        if resultado_ia.revisao_humana:
            estatisticas["revisao_humana"] += 1
            logging.info(
                f"[IA -> Revisão Humana] {id_sol} encaminhado para fila humana (confiança={resultado_ia.confianca:.2f})."
            )

        # Geração de protocolo e persistência SQL
        numero_protocolo = f"CT-2026-{id_sol.replace('SOL-', '')}"
        status_email = notificador.enviar_comprovante(
            destinatario=str(linha["email_cidadao"]).strip(),
            nome=str(linha["nome_cidadao"]).strip(),
            protocolo=numero_protocolo,
            categoria=resultado_ia.categoria,
            prioridade=resultado_ia.prioridade,
        )

        repo_sql.salvar_protocolo({
            "id_solicitacao": id_sol,
            "numero_protocolo": numero_protocolo,
            "nome_cidadao": str(linha["nome_cidadao"]).strip(),
            "email_cidadao": str(linha["email_cidadao"]).strip(),
            "cep": cep_limpo,
            "endereco_enriquecido": endereco_completo,
            "relato": relato,
            "categoria_ia": resultado_ia.categoria,
            "confianca_ia": resultado_ia.confianca,
            "prioridade": resultado_ia.prioridade,
            "revisao_humana": resultado_ia.revisao_humana,
            "status_notificacao": status_email,
        })
        estatisticas["processados_sucesso"] += 1

        # Métricas contra gabarito rotulado
        esperado = str(linha.get("categoria_esperada", "")).strip()
        if esperado and esperado != "nan":
            estatisticas["avaliados_ia"] += 1
            acertou = resultado_ia.categoria == esperado
            if acertou:
                estatisticas["acertos_ia"] += 1
            detalhes_avaliacao.append(
                f"| {id_sol} | {esperado} | {resultado_ia.categoria} | {resultado_ia.confianca:.2f} | {'Acerto' if acertou else 'Erro'} |"
            )

        logging.info(
            f"[Concluído] {id_sol} -> Protocolo: {numero_protocolo} | Categoria: {resultado_ia.categoria} "
            f"({resultado_ia.confianca:.2f}) | Prioridade: {resultado_ia.prioridade} | E-mail: {status_email}"
        )

    # 4. Geração do Relatório de Evidências de Validação
    acuracia = (
        (estatisticas["acertos_ia"] / estatisticas["avaliados_ia"]) * 100
        if estatisticas["avaliados_ia"] > 0
        else 0.0
    )

    relatorio_md = f"""# Relatório de Execução e Evidências de Validação — CitizenTech RPA + IA
**Data/Hora da Execução:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## 1. Resumo Operacional do Fluxo
- **Total de registros lidos (CSV):** {estatisticas['lidos']}
- **Duplicidades barradas (Idempotência):** {estatisticas['duplicados_ignorados']}
- **Registros inválidos descartados com log:** {estatisticas['invalidos_descartados']}
- **Protocolos gravados no Banco SQLite (`{banco_sqlite}`):** {estatisticas['processados_sucesso']}
- **Encaminhados para Revisão Humana (baixa confiança IA):** {estatisticas['revisao_humana']}
- **Fallbacks de API externa tratados sem quebra:** {estatisticas['fallbacks_api']}

## 2. Métricas da Inteligência Artificial (Amostra Rotulada)
- **Amostra válida avaliada:** {estatisticas['avaliados_ia']} solicitações
- **Acertos:** {estatisticas['acertos_ia']} / {estatisticas['avaliados_ia']}
- **Acurácia observada:** {acuracia:.1f}%

| ID | Categoria Esperada | Categoria Prevista (IA) | Confiança | Status |
| :--- | :--- | :--- | :---: | :---: |
{chr(10).join(detalhes_avaliacao)}

## 3. Evidências de Falhas Tratadas com Segurança
{chr(10).join(f'- {item}' for item in falhas_tratadas)}

> Logs detalhados salvos em: `{caminho_log}`
"""
    with open("relatorio_validacao.md", "w", encoding="utf-8") as f:
        f.write(relatorio_md)

    logging.info(f"=== EXECUÇÃO FINALIZADA | Acurácia IA: {acuracia:.1f}% | Relatório: relatorio_validacao.md ===")


if __name__ == "__main__":
    executar_pipeline()