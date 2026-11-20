import logging
import os
import smtplib
import sqlite3
import time
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, Optional
import requests


class ServicoViaCEP:
    """Tema RPA: Integração com API pública com timeout, retry e fallback seguro."""

    def __init__(self, timeout: int = 4, max_tentativas: int = 2):
        self.timeout = timeout
        self.max_tentativas = max_tentativas
        self.cache: Dict[str, Dict[str, str]] = {}

    def consultar_cep(self, cep: str) -> Dict[str, str]:
        cep_limpo = "".join(filter(str.isdigit, str(cep)))
        if cep_limpo in self.cache:
            return self.cache[cep_limpo]

        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                resposta = requests.get(url, timeout=self.timeout)
                resposta.raise_for_status()
                dados = resposta.json()

                if dados.get("erro"):
                    logging.warning(f"[API ViaCEP] CEP inexistente na base pública: {cep_limpo}")
                    resultado = {
                        "status_api": "CEP_NAO_ENCONTRADO",
                        "logradouro": "Não localizado",
                        "bairro": "Não localizado",
                        "cidade_uf": "Não localizado",
                    }
                    self.cache[cep_limpo] = resultado
                    return resultado

                resultado = {
                    "status_api": "OK",
                    "logradouro": dados.get("logradouro") or "Via não especificada",
                    "bairro": dados.get("bairro") or "Centro",
                    "cidade_uf": f"{dados.get('localidade', '')}/{dados.get('uf', '')}",
                }
                self.cache[cep_limpo] = resultado
                return resultado

            except requests.RequestException as erro:
                logging.warning(
                    f"[API ViaCEP] Tentativa {tentativa}/{self.max_tentativas} falhou para CEP {cep_limpo}: {erro}"
                )
                if tentativa < self.max_tentativas:
                    time.sleep(1.0 * tentativa)

        logging.error(f"[API ViaCEP] Falha definitiva ao consultar CEP {cep_limpo}. Aplicando fallback seguro.")
        return {
            "status_api": "FALLBACK_OFFLINE",
            "logradouro": "Pendente verificação",
            "bairro": "Pendente verificação",
            "cidade_uf": "Pendente verificação",
        }


class RepositorioProtocolosSQL:
    """Tema RPA: Persistência em Banco de Dados SQL (SQLite) com garantia de idempotência."""

    def __init__(self, caminho_banco: str):
        self.caminho_banco = caminho_banco
        self._inicializar_tabelas()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.caminho_banco)

    def _inicializar_tabelas(self) -> None:
        with self._conectar() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS protocolos_cidadaos (
                    id_solicitacao TEXT PRIMARY KEY,
                    numero_protocolo TEXT NOT NULL,
                    nome_cidadao TEXT NOT NULL,
                    email_cidadao TEXT NOT NULL,
                    cep TEXT NOT NULL,
                    endereco_enriquecido TEXT NOT NULL,
                    relato TEXT NOT NULL,
                    categoria_ia TEXT NOT NULL,
                    confianca_ia REAL NOT NULL,
                    prioridade TEXT NOT NULL,
                    revisao_humana INTEGER NOT NULL,
                    status_notificacao TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                )
            """)
            conn.commit()

    def ja_processado(self, id_solicitacao: str) -> bool:
        with self._conectar() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM protocolos_cidadaos WHERE id_solicitacao = ?",
                (id_solicitacao,),
            )
            return cursor.fetchone() is not None

    def salvar_protocolo(self, registro: Dict) -> None:
        with self._conectar() as conn:
            conn.execute("""
                INSERT INTO protocolos_cidadaos (
                    id_solicitacao, numero_protocolo, nome_cidadao, email_cidadao,
                    cep, endereco_enriquecido, relato, categoria_ia, confianca_ia,
                    prioridade, revisao_humana, status_notificacao, criado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                registro["id_solicitacao"],
                registro["numero_protocolo"],
                registro["nome_cidadao"],
                registro["email_cidadao"],
                registro["cep"],
                registro["endereco_enriquecido"],
                registro["relato"],
                registro["categoria_ia"],
                registro["confianca_ia"],
                registro["prioridade"],
                1 if registro["revisao_humana"] else 0,
                registro["status_notificacao"],
                datetime.now().isoformat(timespec="seconds"),
            ))
            conn.commit()

    def listar_protocolos(self) -> list[Dict]:
        with self._conectar() as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM protocolos_cidadaos ORDER BY id_solicitacao"
                ).fetchall()
            ]


class NotificadorEmailRPA:
    """Tema RPA: Envio automatizado de e-mail ao cidadão com modo seguro de simulação."""

    def __init__(self, modo_simulacao: bool = True):
        self.modo_simulacao = modo_simulacao
        self.pasta_saida = "emails_enviados"
        os.makedirs(self.pasta_saida, exist_ok=True)

    def enviar_comprovante(self, destinatario: str, nome: str, protocolo: str, categoria: str, prioridade: str) -> str:
        assunto = f"[CitizenTech] Protocolo {protocolo} - Atendimento Registrado"
        corpo = (
            f"Olá, {nome}!\n\n"
            f"Sua solicitação cidadã foi recebida e processada pelo nosso robô de triagem inteligente.\n"
            f"- Protocolo: {protocolo}\n"
            f"- Setor Encaminhado: {categoria}\n"
            f"- Prioridade Estimada: {prioridade}\n\n"
            f"Acompanhe o andamento pelo portal CitizenTech.\n"
            f"Atenciosamente,\nEquipe CitizenTech RPA"
        )

        if self.modo_simulacao:
            caminho_arquivo = os.path.join(self.pasta_saida, f"{protocolo}.txt")
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(f"PARA: {destinatario}\nASSUNTO: {assunto}\n\n{corpo}")
            return "SIMULADO_LOCAL"

        try:
            msg = EmailMessage()
            msg["Subject"] = assunto
            msg["From"] = os.getenv("SMTP_USUARIO", "noreply@citizentech.local")
            msg["To"] = destinatario
            msg.set_content(corpo)

            servidor = os.getenv("SMTP_SERVIDOR", "smtp.gmail.com")
            porta = int(os.getenv("SMTP_PORTA", "587"))
            usuario = os.getenv("SMTP_USUARIO", "")
            senha = os.getenv("SMTP_SENHA", "")

            with smtplib.SMTP(servidor, porta, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(usuario, senha)
                smtp.send_message(msg)
            return "ENVIADO_SMTP"
        except Exception as erro:
            logging.error(f"[E-mail RPA] Falha ao enviar SMTP para {destinatario}: {erro}")
            return "FALHA_SMTP_REGISTRADA"