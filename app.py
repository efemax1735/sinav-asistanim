import base64
import io
import json
import re
import PyPDF2
import google.generativeai as genai
import streamlit as st
import streamlit.components.v1 as components

try:
  from gtts import gTTS

  HAS_TTS = True
except ImportError:
  HAS_TTS = False

st.set_page_config(
    page_title="Akademik Sınav Asistanı", page_icon="🎓", layout="centered"
)

st.title("🎓 Akademik Sınav ve Test Asistanı")
st.write(
    "Ders slaytınızı (PDF) yükleyin; yapay zeka sınav düzeyinde resmi sorular"
    " hazırlasın."
)

api_key = st.text_input("Google Gemini API Anahtarınızı Girin:", type="password")
uploaded_file = st.file_uploader("Ders Notunu Yükle (PDF)", type="pdf")

if "sorular" not in st.session_state:
  st.session_state.sorular = None


def hizli_ses_oynat(metin):
  """Sesli asistanı insan konuşma hızına (1.25x) hızlandırarak oynatır."""
  if not HAS_TTS:
    return
  try:
    tts = gTTS(text=metin, lang="tr")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    b64_audio = base64.b64encode(fp.read()).decode("utf-8")

    # HTML5 Audio + JS PlaybackRate (Doğal insan konuşma temposu)
    html_code = f"""
        <audio id="tts_audio" autoplay controls style="width:100%;">
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById("tts_audio");
            if (audio) {{
                audio.playbackRate = 1.25;
            }}
        </script>
        """
    components.html(html_code, height=65)
  except Exception:
    pass


if uploaded_file is not None and api_key:
  if st.button("🚀 Testi Hazırla"):
    clean_api_key = api_key.strip()
    if not clean_api_key:
      st.error("Lütfen geçerli bir API anahtarı girin!")
      st.stop()

    with st.spinner("Ders notu inceleniyor ve sınav soruları hazırlanıyor..."):
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
              "PDF dosyasından metin okunamadı. Lütfen metin içeren bir PDF"
              " yükleyin."
          )
          st.stop()

        text = text[:15000]

        # Resmi ve Akademik Prompt
        prompt = f"""
                Sen üniversite düzeyinde (vize ve final sınavı) sorular hazırlayan uzman bir akademik sınav koçusun.
                Aşağıdaki ders slaytını okuyarak öğrenciler için resmi dille yazılmış, orta-zor düzeyde 3 adet 5 şıklı çoktan seçmeli soru oluştur.
                
                Kurallar:
                - Dil tamamen resmi, ciddi, net ve akademik sınav standartlarına uygun olmalıdır. Laubali veya samimi ifadeler kesinlikle kullanılmamalıdır.
                - Sorular ders slaytındaki önemli bilgileri, temel tanımları ve mekanizmaları tam ölçmelidir.
                
                Cevaplar için şunları hazırla:
                1. "dogru_tepki": Doğru yanıt için resmi bir onay cümlesi (Ör: "Tebrikler, soruyu doğru yanıtladınız.").
                2. "yanlis_tepki": Yanlış yanıt için açıklayıcı akademik bildirim (Ör: "Maalesef yanlış yanıt. Doğru seçenek ile slayttaki temel kavram uyuşmaktadır.").
                3. "puf_noktasi": Sınavda çıkma ihtimali yüksek olan akademik bilgi notu veya püf noktası.
                
                Çıktıyı SADECE aşağıdaki JSON formatında ver:
                [
                    {{
                        "soru": "Soru metni...",
                        "A": "A şıkkı",
                        "B": "B şıkkı",
                        "C": "C şıkkı",
                        "D": "D şıkkı",
                        "E": "E şıkkı",
                        "dogru_cevap": "A",
                        "dogru_tepki": "Tebrikler, doğru yanıt!",
                        "yanlis_tepki": "Maalesef yanlış yanıt.",
                        "puf_noktasi": "Akademik Püf Noktası: ..."
                    }}
                ]
                
                Ders Notu:
                {text}
                """

        # Hızlı Doğrudan Model Bağlantısı (Ekstra ağ sorgusu yapmadan en hızlı modelleri dener)
        candidate_models = [
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
        ]
        response = None

        for model_name in candidate_models:
          try:
            m_obj = genai.GenerativeModel(
                model_name, generation_config={"response_mime_type": "application/json"}
            )
            res = m_obj.generate_content(prompt)
            if res and res.text:
              response = res
              break
          except Exception:
            continue

        if not response or not response.text:
          st.error(
              "Model bağlantısı sağlanamadı. Lütfen API anahtarınızı kontrol"
              " edin."
          )
          st.stop()

        raw_response = response.text.strip()
        json_match = re.search(r"\[\s*\{.*\}\s*\]", raw_response, re.DOTALL)
        json_str = (
            json_match.group(0)
            if json_match
            else raw_response.replace("```json", "").replace("```", "").strip()
        )

        st.session_state.sorular = json.loads(json_str)
        st.success("Sınav soruları ve sesli açıklamalar hazır!")

      except Exception as e:
        st.error(f"Bir hata oluştu: {e}")

# Soruları ve Sesli Asistanı Gösterme
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

    if st.button("Cevabı Kontrol Et 🔊", key=f"btn_{i
