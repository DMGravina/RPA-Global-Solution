from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


@dataclass
class ResultadoClassificacao:
    categoria: str
    confianca: float
    prioridade: str
    revisao_humana: bool


class ClassificadorCidadaoIA:
    """Modelo de NLP leve (TF-IDF + Regressão Logística) para triagem de demandas cidadãs."""

    def __init__(self, limiar_confianca: float = 0.55):
        self.limiar_confianca = limiar_confianca
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("clf", LogisticRegression(C=3.0, max_iter=500, random_state=42)),
        ])
        self._treinar_modelo_base()

    def _treinar_modelo_base(self) -> None:
        corpus_treino = [
            # Infraestrutura
            ("buraco grande no asfalto da rua atrapalhando o transito", "Infraestrutura"),
            ("calcada quebrada e afundando com risco de queda para pedestres", "Infraestrutura"),
            ("bueiro sem tampa aberto na via publica", "Infraestrutura"),
            ("cratera no meio da avenida apos fortes chuvas", "Infraestrutura"),
            ("ponte de madeira com estrutura danificada e rachaduras", "Infraestrutura"),
            ("guias e sarjetas destruidas na esquina do bairro", "Infraestrutura"),
            ("asfalto cedendo e formando degrau perigoso na pista", "Infraestrutura"),
            ("deslizamento de terra bloqueando parcialmente a estrada", "Infraestrutura"),
            # Iluminacao Publica
            ("poste com lampada queimada deixando a rua escura a noite", "Iluminacao Publica"),
            ("falta de iluminacao publica na praca e no ponto de onibus", "Iluminacao Publica"),
            ("luz do poste piscando sem parar durante toda a madrugada", "Iluminacao Publica"),
            ("luminaria apagada na travessa residencial gera inseguranca", "Iluminacao Publica"),
            ("fiacao solta e poste de luz inclinado na calcada", "Iluminacao Publica"),
            ("avenida completamente no escuro por falha na iluminacao", "Iluminacao Publica"),
            ("lampada de led do poste nao acende ha varias semanas", "Iluminacao Publica"),
            ("escuridao total na passarela de pedestres por falta de luz", "Iluminacao Publica"),
            # Limpeza Urbana
            ("descarte irregular de lixo e entulho na esquina da rua", "Limpeza Urbana"),
            ("caminhao de coleta de lixo nao passou no bairro esta semana", "Limpeza Urbana"),
            ("acumulo de sacos de lixo rasgados na calcada", "Limpeza Urbana"),
            ("galhos de arvore podada e folhas obstruindo a passagem", "Limpeza Urbana"),
            ("terreno cheio de entulho e moveis velhos abandonados", "Limpeza Urbana"),
            ("falta de varricao e limpeza na praca comunitaria", "Limpeza Urbana"),
            ("boca de lobo entupida com garrafas plasticas e sujeira", "Limpeza Urbana"),
            ("lixo acumulado proximo a escola atraindo insetos", "Limpeza Urbana"),
            # Saude e Saneamento
            ("vazamento de esgoto a ceu aberto com mau cheiro forte", "Saude e Saneamento"),
            ("agua parada com foco de larvas do mosquito da dengue", "Saude e Saneamento"),
            ("cano estourado desperdicando agua potavel na rua", "Saude e Saneamento"),
            ("esgoto retornando pelo ralo e contaminando a via publica", "Saude e Saneamento"),
            ("risco de doencas por contaminacao de agua e esgoto", "Saude e Saneamento"),
            ("falta de abastecimento de agua no posto de saude do bairro", "Saude e Saneamento"),
            ("piscina abandonada com agua suja e criadouro de dengue", "Saude e Saneamento"),
            ("rede de saneamento rompida causando alagamento de esgoto", "Saude e Saneamento"),
        ]
        textos = [item[0] for item in corpus_treino]
        categorias = [item[1] for item in corpus_treino]
        self.pipeline.fit(textos, categorias)

    def _definir_prioridade(self, texto: str, categoria: str) -> str:
        texto_lower = texto.lower()
        termos_alta = ["risco", "perigo", "acidente", "esgoto", "dengue", "cratera", "sem tampa", "doencas"]
        if any(termo in texto_lower for termo in termos_alta):
            return "ALTA"
        if categoria in ("Infraestrutura", "Saude e Saneamento"):
            return "MEDIA"
        return "BAIXA"

    def classificar(self, relato: str) -> ResultadoClassificacao:
        probabilidades = self.pipeline.predict_proba([relato])[0]
        classes = self.pipeline.classes_
        indice_maior = probabilidades.argmax()
        confianca = float(probabilidades[indice_maior])
        categoria_prevista = str(classes[indice_maior])

        if confianca < self.limiar_confianca:
            return ResultadoClassificacao(
                categoria="Revisao Humana",
                confianca=round(confianca, 4),
                prioridade="PENDENTE_TRIAGEM",
                revisao_humana=True,
            )

        prioridade = self._definir_prioridade(relato, categoria_prevista)
        return ResultadoClassificacao(
            categoria=categoria_prevista,
            confianca=round(confianca, 4),
            prioridade=prioridade,
            revisao_humana=False,
        )