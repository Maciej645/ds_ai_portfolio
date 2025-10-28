# ===============================
# 📌 Aplikacja Streamlit: ESTYMATOR - Jaki czas osiągniesz w półmaratonie
# ===============================

import os
import io
import json
import boto3
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from langfuse import Langfuse

# ===============================
# ⚙️ Konfiguracja strony
# ===============================
st.set_page_config(
    page_title="ESTYMATOR - Jaki czas osiągniesz w półmaratonie",
    layout="wide",
    page_icon="🏃"
)

# ===============================
# 🔑 Wczytanie zmiennych środowiskowych
# ===============================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3")

# ===============================
# 🚀 Klienci: OpenAI, Langfuse, S3
# ===============================
client = OpenAI(api_key=OPENAI_API_KEY)

langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST,
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=AWS_ENDPOINT_URL_S3,
)

# ===============================
# 📦 Wczytanie modelu z S3
# ===============================
@st.cache_resource
def load_model():
    obj = s3_client.get_object(Bucket="halfmarathon-city", Key="model_pycaret.pkl")
    return joblib.load(io.BytesIO(obj["Body"].read()))

model = load_model()

# ===============================
# 🛠️ Funkcje pomocnicze
# ===============================
def to_seconds(time_str):
    """Konwertuje czas w formacie HH:MM:SS lub MM:SS na sekundy"""
    try:
        parts = list(map(int, str(time_str).split(":")))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        else:
            return None
    except Exception:
        return None

def from_seconds(seconds):
    """Konwertuje sekundy na format HH:MM:SS"""
    if seconds is None:
        return "Brak danych"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"

def normalize_sex(value):
    """Normalizuje płeć do 0 (K) lub 1 (M)"""
    if not value:
        return None
    v = str(value).lower().strip()
    if v in ["m", "mężczyzna", "mezczyzna", "male", "chłopak", "facet"]:
        return 1
    if v in ["k", "kobieta", "female", "dziewczyna", "baba"]:
        return 0
    return None

def parse_user_input(user_input: str):
    """Wyciąga dane użytkownika za pomocą GPT-4o i loguje w Langfuse"""
    trace = langfuse.trace(name="parse_user_input")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś asystentem sportowym. "
                        "Na podstawie danych użytkownika wyciągnij i zwróć wynik TYLKO jako JSON w formacie: "
                        "{"
                        "\"wiek\": int lub null, "
                        "\"płeć\": tekst np. M/K/mężczyzna/kobieta/male/female, "
                        "\"czas_5km\": liczba sekund lub null, "
                        "\"tempo_5km\": liczba sekund na km lub null"
                        "}. "
                        "Nie dodawaj nic poza JSON."
                    )
                },
                {"role": "user", "content": user_input}
            ],
            temperature=0
        )

        parsed_text = response.choices[0].message.content.strip()
        trace.update(output=parsed_text)

        parsed_data = json.loads(parsed_text)
        parsed_data["płeć"] = normalize_sex(parsed_data.get("płeć"))

    except Exception as e:
        parsed_data = {}
        trace.update(error=str(e))

    return parsed_data

# ===============================
# 🎨 UI aplikacji
# ===============================
st.title("🏃 ESTYMATOR - Jaki czas osiągniesz w półmaratonie")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/860/860865.png", width=100)
st.markdown("### ✍️ TWOJE DANE – wpisz kilka informacji o sobie: wiek, płeć , czas na 5 km")

user_input = st.text_area("👉 Podaj dane:", "")

if st.button("OBLICZ CZAS"):
    if not user_input.strip():
        st.warning("⚠️ Podaj swoje dane, aby kontynuować.")
    else:
        parsed_data = parse_user_input(user_input)

        wiek = parsed_data.get("wiek")
        płeć = parsed_data.get("płeć")
        czas_5km = parsed_data.get("czas_5km")
        tempo_5km = parsed_data.get("tempo_5km")

        missing = []
        if wiek is None:
            missing.append("wiek")
        if płeć is None:
            missing.append("płeć")
        if czas_5km is None and tempo_5km is None:
            missing.append("czas na 5 km lub tempo na 5 km")

        if missing:
            st.error(f"⚠️ Uzupełnij brakujące dane: {', '.join(missing)} i naciśnij ponownie przycisk OBLICZ CZAS")
        else:
            if czas_5km is None and tempo_5km:
                czas_5km = tempo_5km * 5

            input_df = pd.DataFrame([{
                "wiek": wiek,
                "płeć_encoded": płeć,
                "5_km_czas_sec": czas_5km,
                "5_km_tempo_sec": tempo_5km if tempo_5km else czas_5km / 5,
            }])

            # ===============================
            # 🧮 Predykcja z pełnym śledzeniem Langfuse
            # ===============================
            trace_pred = langfuse.trace(name="model_prediction")
            try:
                prediction = model.predict(input_df)[0]
                trace_pred.update(output=prediction)
            except Exception as e:
                trace_pred.update(error=str(e))
                st.error(f"❌ Błąd podczas predykcji: {e}")
                prediction = None

            if prediction is not None:
                predicted_seconds = int(prediction)
                predicted_time = from_seconds(predicted_seconds)
                st.success(f"⏱️ Twój przewidywany czas w półmaratonie: **{predicted_time}**")

                # ===============================
                # 📊 Wykres miejsca w półmaratonie
                # ===============================
                obj = s3_client.get_object(Bucket="halfmarathon-city", Key="halfmarathon_wroclaw_2024__final.csv")
                df = pd.read_csv(io.BytesIO(obj["Body"].read()), sep=";")
                df.columns = df.columns.str.strip()

                if "Czas" in df.columns:
                    df["czas_sec"] = df["Czas"].apply(to_seconds)
                    df = df.dropna(subset=["czas_sec"])

                    if not df.empty:
                        plt.figure(figsize=(10, 5))
                        plt.hist(df["czas_sec"], bins=30, alpha=0.7, label="Uczestnicy")
                        plt.axvline(predicted_seconds, color="red", linestyle="--", label=f"Twój czas: {predicted_time}")
                        plt.xlabel("Czas [HH:MM:SS]")
                        plt.ylabel("Liczba uczestników")
                        plt.title("Twoje miejsce wśród uczestników półmaratonu Wrocław 2024")
                        plt.legend()
                        plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: from_seconds(x)))
                        st.pyplot(plt.gcf())
                    else:
                        st.info("ℹ️ Brak danych referencyjnych do wygenerowania wykresu.")
                else:
                    st.info(f"ℹ️ Kolumny dostępne w CSV: {list(df.columns)}")



 