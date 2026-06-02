%%writefile vaxscope_inference.py

import re
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer, pipeline

CHECKPOINT_PATH = "vaxscope_pubmedbert_v1.pt"
QA_MODEL_NAME = "deepset/roberta-base-squad2"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
THRESHOLD = 0.5
DEBUG = False
QA_SCORE_THRESHOLD = 0.02

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location=DEVICE,
    weights_only=False
)

MODEL_NAME = checkpoint["model_name"]
MAX_LEN = checkpoint["max_len"]
LABELS = checkpoint["labels"]

SINGLELABEL_FIELDS = ["disease"]

MULTILABEL_FIELDS = [
    "topic",
    "study_type",
    "review_type",
    "population",
    "outcome"
]

IS_LONGFORMER = "longformer" in MODEL_NAME.lower()


# =========================================================
# MODEL
# =========================================================

class VaxScopeClassifier(nn.Module):

    def __init__(self):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(MODEL_NAME)

        hidden = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(0.1)

        self.heads = nn.ModuleDict({
            field: nn.Linear(hidden, len(space))
            for field, space in LABELS.items()
        })

    def forward(self, input_ids, attention_mask):

        if IS_LONGFORMER:

            global_attention_mask = torch.zeros_like(input_ids)
            global_attention_mask[:, 0] = 1

            outputs = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                global_attention_mask=global_attention_mask
            )

        else:

            outputs = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

        cls = self.dropout(outputs.last_hidden_state[:, 0])

        return {
            field: head(cls)
            for field, head in self.heads.items()
        }


tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = VaxScopeClassifier().to(DEVICE)

model.load_state_dict(checkpoint["model_state_dict"])

model.eval()


# =========================================================
# QA PIPELINE
# =========================================================

qa = pipeline(
    "question-answering",
    model=QA_MODEL_NAME,
    tokenizer=QA_MODEL_NAME,
    device=0 if torch.cuda.is_available() else -1
)


# =========================================================
# DATE NORMALIZATION
# =========================================================

MONTH_MAP = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12"
}


def normalize_date(raw):

    if not raw:
        return None

    raw = raw.strip()

    # dd/mm/yyyy
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", raw)

    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # Month DD, YYYY
    m = re.search(
        r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b",
        raw
    )

    if m:

        month = MONTH_MAP.get(m.group(1).lower())

        if month:

            day = int(m.group(2))

            return f"{m.group(3)}-{month}-{day:02d}"

    # yyyy-mm-dd
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", raw)

    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Month YYYY
    m = re.search(r"\b([A-Za-z]+)\s+(\d{4})\b", raw)

    if m:

        month = MONTH_MAP.get(m.group(1).lower())

        if month:
            return f"{m.group(2)}-{month}-01"

    return None


# =========================================================
# LABEL PREDICTION
# =========================================================

def predict_labels(text):

    enc = tokenizer(
        text,
        truncation=True,
        padding=True,
        max_length=MAX_LEN,
        return_tensors="pt"
    )

    input_ids = enc["input_ids"].to(DEVICE)
    attention_mask = enc["attention_mask"].to(DEVICE)

    with torch.no_grad():

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

    result = {}

    # single-label
    for field in SINGLELABEL_FIELDS:

        idx = torch.argmax(outputs[field], dim=1).item()

        result[field] = LABELS[field][idx]

    # multi-label
    for field in MULTILABEL_FIELDS:

        probs = torch.sigmoid(outputs[field])[0]

        result[field] = [
            LABELS[field][i]
            for i, p in enumerate(probs)
            if p.item() > THRESHOLD
        ]

    return result


# =========================================================
# QA QUESTIONS
# =========================================================

QA_QUESTIONS = {

    "num_studies": [
        "How many studies were included?",
        "How many studies were identified?",
        "How many studies met the inclusion criteria?",
        "How many papers were included?"
    ],

    "num_participants": [
        "How many participants were included?",
        "How many patients were included?",
        "How many subjects were enrolled?",
        "How many person-seasons were enrolled?",
        "What was the sample size?"
    ],

    "date_of_last_lit": [
        "When was the last search performed?",
        "When was the last automatic search performed?",
        "Until what date was the literature search conducted?",
        "What was the date of the last literature search?"
    ],
}


# =========================================================
# RULE-BASED SLOT VALIDATION
# =========================================================

def extract_regex_slots(text):

    result = {
        "num_studies": None,
        "num_participants": None,
        "date_of_last_lit": None
    }

    # -----------------------------
    # NUM STUDIES
    # -----------------------------

    NUMBER_WORDS = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "thirty": 30,
        "fourty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90
    }

    patterns_studies = [
        r"\b([A-Za-z]+)\s+studies\s+(?:were\s+)?(?:included|identified|selected)",
        r"\b(\d+)\s*\([^)]*\)\s+studies\s+(?:were\s+)?(?:included|identified|selected)",
        r"\b(\d+)\s+studies\s+(?:were\s+)?(?:included|identified|selected)",
        r"corresponding to\s+(\d+)\s+studies",
        r"\b(\d+)\s+studies\s+met the inclusion criteria",
        r"\b(\d+)\s+observational studies",
        r"\b(?:from|including|based on)\s+(\d+)\s+(?:real-world evidence\s+)?studies\b",
        r"\b(\d+)\s+(?:real-world evidence\s+)?\(?RWE\)?\s+studies\b",
        r"\b(\d+)\s+(?:real-world evidence\s+)?studies\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:real-world evidence\s+)?\(?RWE\)?\s+studies\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:real-world evidence\s+)?studies\b",
    ]

    for pattern in patterns_studies:
        m = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        if m:
            value = m.group(1)

            if value.isdigit():
                result["num_studies"] = int(value)
            else:
                value = value.lower()

                if value in NUMBER_WORDS:
                    result["num_studies"] = NUMBER_WORDS[value]
                else:
                    continue  # ← bu pattern işe yaramadı, sonrakini dene

            break  # ← değer bulundu, döngüden çık

    # -----------------------------
    # PARTICIPANTS
    # -----------------------------

    million_match = re.search(
        r"(\d+)\s+million participants",
        text,
        re.IGNORECASE
    )

    if million_match:
        result["num_participants"] = (
            int(million_match.group(1)) * 1000000
        )

    else:
        patterns_participants = [
            r"\b(\d[\d,]*)\s+person-seasons\b",
            r"\b(\d[\d,]*)\s+participants\b",
            r"\b(\d[\d,]*)\s+patients\b",
            r"\b(\d[\d,]*)\s+subjects\b",
            r"\b(\d[\d,]*)\s+individuals\b",
            r"\b(\d[\d,\.]*)\s+study participants\b",
        ]

        for pattern in patterns_participants:
            m = re.search(pattern, text, re.IGNORECASE)

            if m:
                result["num_participants"] = int(
                    m.group(1).replace(",", "").replace(".", "")
                )
                break

    # -----------------------------
    # DATE
    # -----------------------------

    patterns_date = [
        r"last automatic search was performed on\s+(\d{2})/(\d{2})/(\d{4})",
        r"last search was performed on\s+(\d{2})/(\d{2})/(\d{4})",
        r"published until\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        r"search.*?(?:until|up to|through|to)\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        r"search.*?(?:until|up to|through|to)\s+([A-Za-z]+\s+\d{4})",
        r"search.*?(?:until|up to|through|to)\s+(\d{2})/(\d{2})/(\d{4})",
        r"(?:between|from).*?and\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"as of\s+([A-Za-z]+\s+\d{4})"
    ]

    for pattern in patterns_date:
        m = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        if m:
            parsed = normalize_date(m.group(1))

            if parsed:
                result["date_of_last_lit"] = parsed
                break

    return result


# =========================================================
# PARTICIPANT OVERRIDE
# =========================================================

def extract_num_participants(text):

    # million handling
    m = re.search(
        r"(\d+)\s+million participants",
        text,
        re.IGNORECASE
    )

    if m:
        return int(m.group(1)) * 1000000

    patterns = [
        r"Taken together, the\s+(\d[\d,]*)\s+person-seasons",
        r"\b(\d[\d,]*)\s+person-seasons\b",
        r"\b(\d[\d,]*)\s+participants\b",
        r"\b(\d[\d,]*)\s+patients\b",
        r"\b(\d[\d,]*)\s+subjects\b",
        r"\b(\d[\d,]*)\s+individuals\b",
    ]

    for pattern in patterns:

        m = re.search(pattern, text, re.IGNORECASE)

        if m:

            value = int(m.group(1).replace(",", "").replace(".", "")
)

            if value >= 50:
                return value

    return None


# =========================================================
# NUMERIC SLOT PREDICTION
# =========================================================

def predict_numeric_slots(text):

    result = {
        "num_studies": None,
        "num_participants": None,
        "date_of_last_lit": None
    }

    context = text[:20000]

    for field, questions in QA_QUESTIONS.items():

        best_output = None

        for question in questions:

            output = qa(
                question=question,
                context=context
            )

            if (
                best_output is None
                or output["score"] > best_output["score"]
            ):
                best_output = output

        answer = best_output["answer"]
        score = best_output["score"]

        if DEBUG:
            print(field, "=>", answer, "| score:", score)

        if field == "date_of_last_lit":
            parsed = normalize_date(answer)
            if parsed:
                result[field] = parsed
            continue

        if score < QA_SCORE_THRESHOLD:
            continue

        if field == "num_studies":
            m = re.search(r"\d[\d,]*", answer)
            if m:
                result[field] = int(m.group().replace(",", ""))

        elif field == "num_participants":
            continue

    participant_value = extract_num_participants(text)
    if participant_value is not None:
        result["num_participants"] = participant_value

    regex_result = extract_regex_slots(text)
    for key, value in regex_result.items():
        if value is not None:
            result[key] = value

    return result


# =========================================================
# MAIN PIPELINE
# =========================================================

def predict_vaxscope(
    title,
    abstract,
    full_text=None,
    extra_classification_chunks=None
):

    # classification text
    classification_parts = [
        title.strip(),
        abstract.strip()
    ]

    if extra_classification_chunks:

        classification_parts.extend([

            chunk.strip()

            for chunk in extra_classification_chunks

            if chunk and chunk.strip()
        ])

    classification_text = "\n".join([
        p for p in classification_parts if p
    ])

    # QA text
    qa_text = (
        full_text.strip()
        if full_text
        else classification_text
    )

    labels = predict_labels(classification_text)

    slots = predict_numeric_slots(qa_text)

    return {
        **labels,
        **slots
    }


# =========================================================
# POSTPROCESSING
# =========================================================

def postprocess_prediction(prediction):

    topics = prediction.get("topic", [])

    if "efficacy_effectiveness" not in topics:
        prediction["outcome"] = []

    prediction["study_type"] = [
        s.replace("-", "_")
        for s in prediction.get("study_type", [])
    ]

    populations = prediction.get("population", [])

    if not populations:
        prediction["population"] = ["all_age_groups"]

    elif (
        "children" in populations
        and "adolescents" in populations
        and "adults" in populations
        and "elderly" in populations
    ):
        prediction["population"] = ["all_age_groups"]

    return prediction