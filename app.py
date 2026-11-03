import io
import json
import re
import PyPDF2
import google.generativeai as genai
import streamlit as st

try:
  from gtts import gTTS

  HAS_TTS = True
except ImportError:
  HAS_TTS = False

st.set_page_config(
    page_title="Educato Sınav Asistanı", page_icon="💊", layout="centered"
)

st.title("💊 Educato Tarzı Sesli Sınav Asistanı")
st.write("Slaytını yükle; esprili sesli asistan seni sınava hazırlasın!")

api_key = st.text_input("Google Gemini API Anahtarınızı Girin:", type="password")
uploaded_file = st.file_uploader("Ders Notunu Yükle (PDF)", type="pdf")

if "sorular" not in st.session_state:
  st.session_state.sorular = None


def metni_seslendir(metin):
  if not HAS_TTS:
    return None
  try:
    tts = gTTS(text=metin, lang="tr")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp
  except Exception:
    return None


if uploaded_file is not None and api_key:
  if st.button("🚀 Testi Hazırla"):
    clean_api_key = api_key.strip()
    if not clean_api_key:
      st.error("Lütfen geçerli bir API anahtarı girin!")
      st.stop()

    with st.spinner(
        "Asistan aktif modelleri sorguluyor ve soruları hazırlıyor..."
    ):
      try:
        genai.configure(api_key=clean_api_key)

        # PDF Metnini Çıkarma
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
          t = page.extract_text()
          if t:
            text += t + "\n"

        if not text.strip():
          st.error(
              "PDF'ten metin okunamadı. Lütfen PDF'in resim/taranmış belge olmadığından"
              " emin olun."
          )
          st.stop()

        text = text[:15000]

        prompt = f"""
                Sen Educato tarzında, öğrenci diliyle konuşan, çok esprili, hafif argolu, samimi, komik ama bilgili bir sınav koçusun.
                Aşağıdaki ders slaytını okuyarak 3 adet 5 şıklı çoktan seçmeli soru oluştur.
                
                Cevaplar için şunları hazırla:
                1. "dogru_tepki": Öğrenci doğru bilirse onu gaza getirecek komik, hafif argolu tebrik cümlesi.
                2. "yanlis_tepki": Öğrenci yanlış yaparsa tatlı-sert dalga geçecek esprili eleştiri.
                3. "puf_noktasi": Konunun sınavda kesin çıkacak püf noktası veya akılda kalıcı şifresi/taktiği.
                
                Çıktıyı SADECE aşağıdaki JSON formatında ver:
                [
                    {{
                        "soru": "Soru metni",
                        "A": "A şıkkı",
                        "B": "B şıkkı",
                        "C": "C şıkkı",
                        "D": "D şıkkı",
                        "E": "E şıkkı",
                        "dogru_cevap": "A",
                        "dogru_tepki": "Helal be! Konuyu yutmuşsun, vizede derece geliyor!",
                        "yanlis_tepki": "Kanka naptın ya? Bu cevapla vizeden 20 alıp büte kalırız, gözünü seveyim dikkatli oku!",
                        "puf_noktasi": "Püf Noktası: Bu mekanizmayı unutma!"
                    }}
                ]
                
                Ders Notu:
                {text}
                """

        # Hesabındaki aktif modelleri canlı sorgula
        available_models = []
        for m in genai.list_models():
          if "generateContent" in m.supported_generation_methods:
            available_models.append(m.name)

        if not available_models:
          st.error("API anahtarınızla erişilebilen aktif bir model bulunamadı.")
          st.stop()

        # Strict JSON çıktı yapılandırması
        generation_config = {"response_mime_type": "application/json"}

        response = None
        for model_name in available_models:
          try:
            m_obj = genai.GenerativeModel(
                model_name, generation_config=generation_config
            )
            res = m_obj.generate_content(prompt)
            if res and res.text:
              response = res
              break
          except Exception:
            try:
              m_obj = genai.GenerativeModel(model_name)
              res = m_obj.generate_content(prompt)
              if res and res.text:
                response = res
                break
            except Exception:
              continue

        if not response or not response.text:
          st.error("Modelden yanıt alınamadı.")
          st.stop()

        raw_response = response.text.strip()

        # Regex ile sadece JSON dizisini cımbızla çekme
        json_match = re.search(r"\[\s*\{.*\}\s*\]", raw_response, re.DOTALL)
        if json_match:
          json_str = json_match.group(0)
        else:
          json_str = (
              raw_response.replace("```json", "").replace("```", "").strip()
          )

        st.session_state.sorular = json.loads(json_str)
        st.success("Test ve sesli yanıtlar hazır!")

      except Exception as e:
        st.error(f"Genel Hata: {e}")

if st.session_state.sorular:
  st.write("---")
  for i, q in enumerate(st.session_state.sorular):
    st.subheader(f"Soru {i+1}")
    st.write(q["soru"])

    secenekler = [
        f"A) {q['A']}",
        f"B) {q['B']}",
        f"C) {q['C']}",
        f"D) {q['D']}",
        f"E) {q['E']}",
    ]
    secim = st.radio("Cevabınız:", secenekler, key=f"soru_{i}", index=None)

    if st.button("Cevabı Kontrol Et 🔊", key=f"btn_{i}"):
      if secim:
        secilen_harf = secim.split(")")[0]
        if secilen_harf == q["dogru_cevap"]:
          st.success(f"✅ {q['dogru_tepki']}")
          ses_metni = f"{q['dogru_tepki']} {q['puf_noktasi']}"
        else:
          st.error(
              f"❌ {q['yanlis_tepki']} (Doğru Cevap: {q['dogru_cevap']})"
          )
          ses_metni = (
              f"{q['yanlis_tepki']} Doğru cevap {q['dogru_cevap']} şıkkıydı."
              f" {q['puf_noktasi']}"
          )

        st.info(f"💡 **Taktik / Püf Noktası:** {q['puf_noktasi']}")

        audio_file = metni_seslendir(ses_metni)
        if audio_file:
          st.audio(audio_file, format="audio/mp3", autoplay=True)
      else:
        st.warning("Önce bir şık seç kanka!")
    st.write("---")
