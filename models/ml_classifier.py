"""
MLClassifier — Classificador de URLs baseado em Machine Learning.
Treina Random Forest com features extraídas de URLs (offline, sem acessar páginas).
Complementa a análise heurística com pesos aprendidos dos datasets.

Fluxo:
1. Treina com PhiUSIIL ou dataset similar (URL + label)
2. Extrai features de cada URL usando o mesmo pipeline do HeuristicAnalyzer
3. Prediz probabilidade de phishing/malicioso (0.0–1.0)
4. Resultado é COMPLEMENTAR à heurística, nunca substitui
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

import tldextract

from config.settings import (
    DATASETS_DOWNLOAD_DIR, BASE_DIR,
    TRIGGER_WORDS, URL_SHORTENERS, HIGH_RISK_TLDS, COMMON_TLDS,
)
from utils.logger import setup_logger
from utils.url_utils import (
    count_percent_encoding,
    is_ipv4_address,
    shannon_entropy as _shannon_entropy,
)

logger = setup_logger("ml_classifier")

MODEL_PATH = BASE_DIR / "models" / "trained_model.joblib"
FEATURE_NAMES_PATH = BASE_DIR / "models" / "feature_names.txt"


@dataclass
class MLPrediction:
    """Resultado da predição ML."""
    available: bool = False
    probability_malicious: float = 0.0
    probability_safe: float = 0.0
    prediction: str = ""          # "safe", "malicious"
    confidence: float = 0.0       # 0.0–1.0
    model_accuracy: float = 0.0   # Acurácia do modelo no teste
    error: str = ""


@dataclass
class TrainingResult:
    """Resultado do treinamento do modelo."""
    success: bool = False
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    samples_train: int = 0
    samples_test: int = 0
    features_used: int = 0
    error: str = ""


# === Feature extraction (URL-only, sem acessar página) ===

def extract_url_features(url: str) -> dict:
    """
    Extrai features numéricas de uma URL para uso no classificador ML.
    Retorna dict com 25 features compatíveis com o treinamento.
    Usa APENAS a URL — não acessa a página.
    """
    features = {}

    # Parse básico
    try:
        if not url.startswith(("http://", "https://")):
            url_parsed = f"https://{url}"
        else:
            url_parsed = url
        parsed = urlparse(url_parsed)
    except Exception:
        parsed = urlparse("https://invalid.com")

    hostname = parsed.hostname or ""
    path = parsed.path or ""
    query = parsed.query or ""
    scheme = parsed.scheme or ""

    # Separa domínio e subdomínios com tldextract (mesmo motor do URLParser).
    # Split ingênuo por "." quebraria sufixos compostos: em "bb.com.br" o TLD
    # real é "com.br" e não há subdomínio, mas o split daria tld="br" e
    # subdomain="bb" — errado justamente nos domínios brasileiros.
    extracted = tldextract.extract(url_parsed)
    tld = extracted.suffix or ""
    subdomain = extracted.subdomain or ""

    # 1. Comprimento da URL
    features["url_length"] = len(url)

    # 2. Comprimento do domínio
    features["domain_length"] = len(hostname)

    # 3. IP em vez de domínio (valida os octetos: "999.999.999.999" não é IP)
    features["is_ip"] = 1 if is_ipv4_address(hostname) else 0

    # 4. HTTPS
    features["is_https"] = 1 if scheme == "https" else 0

    # 5. Número de subdomínios
    features["num_subdomains"] = len(subdomain.split(".")) if subdomain else 0

    # 6. Comprimento do path
    features["path_length"] = len(path)

    # 7. Comprimento da query
    features["query_length"] = len(query)

    # 8. Número de pontos na URL
    features["num_dots"] = url.count(".")

    # 9. Número de hífens
    features["num_hyphens"] = url.count("-")

    # 10. Número de underscores
    features["num_underscores"] = url.count("_")

    # 11. Número de barras
    features["num_slashes"] = url.count("/")

    # 12. Número de dígitos na URL
    features["num_digits"] = sum(1 for c in url if c.isdigit())

    # 13. Proporção de dígitos
    features["digit_ratio"] = features["num_digits"] / max(1, len(url))

    # 14. Número de letras
    features["num_letters"] = sum(1 for c in url if c.isalpha())

    # 15. Proporção de letras
    features["letter_ratio"] = features["num_letters"] / max(1, len(url))

    # 16. Número de caracteres especiais
    special = sum(1 for c in url if not c.isalnum() and c not in ":/.-_?=&")
    features["num_special_chars"] = special

    # 17. Entropia da URL
    features["url_entropy"] = round(_shannon_entropy(url), 4)

    # 18. Entropia do domínio
    features["domain_entropy"] = round(_shannon_entropy(hostname), 4)

    # 19. TLD de risco
    features["tld_is_risky"] = 1 if tld.lower() in HIGH_RISK_TLDS else 0

    # 20. TLD comum
    features["tld_is_common"] = 1 if tld.lower() in COMMON_TLDS else 0

    # 21. URL encurtada
    features["is_shortener"] = 1 if hostname.lower() in URL_SHORTENERS else 0

    # 22. Número de trigger words
    url_lower = url.lower()
    features["num_trigger_words"] = sum(1 for w in TRIGGER_WORDS if w in url_lower)

    # 23. Tem @ na URL
    features["has_at_symbol"] = 1 if "@" in url else 0

    # 24. Número de parâmetros na query
    try:
        params = parse_qs(query)
        features["num_params"] = len(params)
    except Exception:
        features["num_params"] = 0

    # 25. Percent-encoding count
    features["num_percent_encoding"] = count_percent_encoding(url)

    return features


FEATURE_ORDER = [
    "url_length", "domain_length", "is_ip", "is_https",
    "num_subdomains", "path_length", "query_length", "num_dots",
    "num_hyphens", "num_underscores", "num_slashes", "num_digits",
    "digit_ratio", "num_letters", "letter_ratio", "num_special_chars",
    "url_entropy", "domain_entropy", "tld_is_risky", "tld_is_common",
    "is_shortener", "num_trigger_words", "has_at_symbol", "num_params",
    "num_percent_encoding",
]


class MLClassifier:
    """
    Classificador ML para URLs maliciosas.
    Usa Random Forest treinado com features extraídas de URLs.
    O modelo é salvo/carregado com joblib para evitar re-treinamento.
    """

    def __init__(self):
        self._model = None
        self._accuracy = 0.0
        self._is_trained = False
        self._sklearn_available = False
        self._feature_order = list(FEATURE_ORDER)

        try:
            import sklearn  # noqa: F401
            self._sklearn_available = True
        except ImportError:
            logger.warning(
                "scikit-learn não instalado. Classificador ML desabilitado. "
                "Instale com: pip install scikit-learn"
            )

    @property
    def is_available(self) -> bool:
        """Verifica se o classificador está disponível e treinado."""
        return self._sklearn_available and self._is_trained

    @property
    def is_sklearn_installed(self) -> bool:
        return self._sklearn_available

    def load_model(self) -> bool:
        """Carrega modelo pré-treinado do disco."""
        if not self._sklearn_available:
            return False

        if not MODEL_PATH.exists():
            return False

        try:
            import joblib
            data = joblib.load(MODEL_PATH)
            self._model = data["model"]
            self._accuracy = data.get("accuracy", 0.0)
            self._feature_order = self._load_saved_feature_order(data.get("features"))
            self._is_trained = True
            logger.info(
                "Modelo ML carregado de %s (acurácia: %.2f%%, %d features)",
                MODEL_PATH, self._accuracy * 100, len(self._feature_order),
            )
            return True
        except Exception as e:
            logger.error("Erro ao carregar modelo ML: %s", e)
            return False

    def train(self, dataset_path: Optional[str] = None,
              max_samples: int = 100_000) -> TrainingResult:
        """
        Treina o classificador Random Forest com dataset de URLs rotuladas.
        Usa PhiUSIIL por padrão se disponível.
        """
        if not self._sklearn_available:
            return TrainingResult(
                error="scikit-learn não instalado. Execute: pip install scikit-learn"
            )

        import csv
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        import joblib

        # Localiza dataset
        if dataset_path:
            ds_path = Path(dataset_path)
        else:
            ds_path = self._find_training_dataset()

        if not ds_path or not ds_path.exists():
            return TrainingResult(
                error=(
                    "Nenhum dataset de treinamento encontrado.\n"
                    "Coloque PhiUSIIL_Phishing_URL_Dataset.csv em datasets/downloads/"
                )
            )

        logger.info("Treinando modelo ML com %s...", ds_path.name)

        # Extrai features de cada URL
        X = []
        y = []
        count = 0

        try:
            with open(ds_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if count >= max_samples:
                        break

                    # Busca coluna URL (case-insensitive, tolera BOM)
                    url = ""
                    label_str = ""
                    for key, val in row.items():
                        clean_key = key.strip().strip("\ufeff").lower()
                        if clean_key == "url" and not url:
                            url = val.strip() if val else ""
                        elif clean_key == "label" and not label_str:
                            label_str = val.strip() if val else ""

                    if not url or not label_str:
                        continue

                    try:
                        label = int(float(label_str))
                    except (ValueError, TypeError):
                        if label_str.lower() in ("phishing", "malicious", "bad", "spam"):
                            label = 1
                        elif label_str.lower() in ("legitimate", "benign", "good", "safe"):
                            label = 0
                        else:
                            continue

                    # Normaliza: 1 = malicioso, 0 = seguro
                    if label not in (0, 1):
                        continue

                    features = extract_url_features(url)
                    feature_vec = [features.get(name, 0) for name in FEATURE_ORDER]
                    X.append(feature_vec)
                    y.append(label)
                    count += 1

        except Exception as e:
            return TrainingResult(error=f"Erro ao ler dataset: {e}")

        if len(X) < 100:
            return TrainingResult(
                error=f"Dataset muito pequeno ({len(X)} amostras). Mínimo: 100."
            )

        logger.info("Features extraídas de %d URLs. Treinando...", len(X))

        # Split treino/teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        # Treina Random Forest
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Avalia
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # Salva modelo
        try:
            joblib.dump(
                {"model": model, "accuracy": acc, "features": FEATURE_ORDER},
                MODEL_PATH,
            )
            FEATURE_NAMES_PATH.write_text(
                "\n".join(FEATURE_ORDER) + "\n",
                encoding="utf-8",
            )
            logger.info("Modelo salvo em %s", MODEL_PATH)
        except Exception as e:
            logger.error("Erro ao salvar modelo: %s", e)

        self._model = model
        self._accuracy = acc
        self._is_trained = True
        self._feature_order = list(FEATURE_ORDER)

        result = TrainingResult(
            success=True,
            accuracy=acc,
            precision=prec,
            recall=rec,
            f1=f1,
            samples_train=len(X_train),
            samples_test=len(X_test),
            features_used=len(FEATURE_ORDER),
        )

        logger.info(
            "Modelo treinado — Acc: %.2f%%, Prec: %.2f%%, Rec: %.2f%%, F1: %.2f%%",
            acc * 100, prec * 100, rec * 100, f1 * 100,
        )

        return result

    def predict(self, url: str) -> MLPrediction:
        """
        Prediz se uma URL é maliciosa usando o modelo treinado.
        Retorna MLPrediction com probabilidades.
        """
        if not self._is_trained or not self._model:
            return MLPrediction(
                available=False,
                error="Modelo ML não treinado. Use o módulo Configurações para treinar.",
            )

        try:
            features = extract_url_features(url)
            feature_vec = [features.get(name, 0) for name in self._feature_order]

            # Predição com probabilidade
            proba = self._model.predict_proba([feature_vec])[0]

            classes = list(getattr(self._model, "classes_", [0, 1]))
            proba_map = dict(zip(classes, proba))
            prob_safe = float(proba_map.get(0, 0.0))
            prob_malicious = float(proba_map.get(1, 0.0))
            prediction = "malicious" if prob_malicious > 0.5 else "safe"
            confidence = max(prob_safe, prob_malicious)

            return MLPrediction(
                available=True,
                probability_malicious=round(prob_malicious, 4),
                probability_safe=round(prob_safe, 4),
                prediction=prediction,
                confidence=round(confidence, 4),
                model_accuracy=self._accuracy,
            )

        except Exception as e:
            return MLPrediction(
                available=False,
                error=f"Erro na predição: {e}",
            )

    def get_feature_importance(self) -> list[tuple[str, float]]:
        """Retorna features mais importantes do modelo (top 10)."""
        if not self._is_trained or not self._model:
            return []

        try:
            importances = self._model.feature_importances_
            pairs = list(zip(self._feature_order, importances))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs[:10]
        except Exception:
            return []

    def _load_saved_feature_order(self, saved_features: Optional[list] = None) -> list[str]:
        """Carrega a ordem de features persistida com o modelo, quando disponível."""
        if isinstance(saved_features, list) and saved_features:
            return [str(name) for name in saved_features]

        if FEATURE_NAMES_PATH.exists():
            try:
                feature_names = [
                    line.strip()
                    for line in FEATURE_NAMES_PATH.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if feature_names:
                    return feature_names
            except OSError as e:
                logger.warning("Falha ao ler %s: %s", FEATURE_NAMES_PATH, e)

        return list(FEATURE_ORDER)

    def _find_training_dataset(self) -> Optional[Path]:
        """Localiza dataset de treinamento na pasta downloads."""
        download_dir = Path(DATASETS_DOWNLOAD_DIR)

        # Prioridade de datasets
        candidates = [
            "PhiUSIIL_Phishing_URL_Dataset.csv",
            "phiusiil.csv",
            "dataset_with_all_features v2.csv",
            "dataset_with_all_features.csv",
        ]

        for name in candidates:
            path = download_dir / name
            if path.exists():
                return path

        # Busca qualquer CSV grande na pasta
        for path in download_dir.glob("*.csv"):
            if path.stat().st_size > 1_000_000:  # > 1MB
                return path

        return None
