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

# Times New Roman Font ve Büyük Okunaklı Punto Tasarımı
st.markdown(
    """
    <style>
        html, body, p, span, label, div, [class*="st-"] {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 20px !important;
        }
        h1 {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 32px !important;
            font-weight: bold !important;
        }
        h2, h3 {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 24px !important;
            font-weight: bold !important;
        }
        .stButton button {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 20px !important;
            padding: 10px 20px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
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
  if not HAS_TTS:
    return
  try:
    tts = gTTS(text=metin, lang="tr")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    b64_audio = base64.b64encode(fp.read()).decode("utf-8")
    html_code = (
        '<audio id="tts_audio" autoplay controls style="width:100%;">'
        f'<source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">'
        "</audio>"
        "<script>"
        'var audio = document.getElementById("tts_audio");'
        "if (audio) { audio.playbackRate = 1.25; }"
        "</script>"
    )
    components.html(html_code, height=70)
  except Exception:
    pass


if uploaded_file is not None and api_key:
  if st.button("🚀 Testi Hazırla"):
    clean_api_key = api_key.strip()
    if not clean_api_key:
      st.error("Lütfen geçerli bir API anahtarı girin!")
      st.stop()

    with st.spinner("Ders notu inceleniyor ve sorular hazırlanıyor..."):
      try:
        genai.configure(api_key=clean_api_key)

        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
          t = page.extract_text()
          if t:
            text += t + "\n"

        if not text.strip():
          st.error("PDF dosyasından metin okunamadı.")
          st.stop()

        text = text[:15000]

        prompt = (
            "Sen üniversite düzeyinde (vize ve final sınavı) sorular hazırlayan"
            " uzman bir akademik sınav koçusun.\nAşağıdaki ders slaytını okuyarak"
            " öğrenciler için resmi dille yazılmış, orta-zor düzeyde 3 adet 5"
            " şıklı çoktan seçmeli soru oluştur.\n\nKurallar:\n- Dil tamamen"
            " resmi, ciddi, net ve akademik sınav standartlarına uygun"
            " olmalıdır.\n- Cevaplar için resmi ve açıklayıcı ifadeler"
            " kullan.\n\nÇıktıyı SADECE aşağıdaki JSON formatında ver:\n[\n "
            " {\n    \"soru\": \"Soru metni...\",\n    \"A\": \"A şıkkı\", \"B\":"
            ' "B şıkkı", "C": "C şıkkı", "D": "D şıkkı", "E": "E şıkkı",\n   '
            ' "dogru_cevap": "A",\n    "dogru_tepki": "Tebrikler, doğru'
            ' yanıt!",\n    "yanlis_tepki": "Maalesef yanlış yanıt.",\n   '
            ' "puf_noktasi": "Akademik Püf Noktası: ..."\n  }\n]\n\nDers'
            f" Notu:\n{text}"
        )

        models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
        response = None
        last_err = None

        for m_name in models_to_try:
          try:
            m_obj = genai.GenerativeModel(m_name)
            res = m_obj.generate_content(prompt)
            if res and res.text:
              response = res
              break
          except Exception as err:
            last_err = err
            continue

        if not response or not response.text:
          st.error(f"API / Model Hatası Detayı: {last_err}")
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
        st.error(f"İşlem sırasında hata oluştu: {e}")

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
    secim = st.radio("Cevabınız:", secenekler, key=f"rad_{i}", index=None)

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
              f"{q['yanlis_tepki']} Doğru cevap {q['dogru_cevap']} şıkkıdır."
              f" {q['puf_noktasi']}"
          )

        st.info(f"💡 **Sınav Püf Noktası:** {q['puf_noktasi']}")
        hizli_ses_oynat(ses_metni)
      else:
        st.warning("Lütfen bir seçenek işaretleyin.")
    st.write("---")
