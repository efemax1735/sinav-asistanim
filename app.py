import base64
import io
import json
import re
import time
import PyPDF2
import streamlit as st
import streamlit.components.v1 as components

# SDK Kontrolü
try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai_legacy
    USE_NEW_SDK = False

try:
    from gtts import gTTS
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

st.set_page_config(
    page_title="Akademik Sınav Asistanı", 
    page_icon="🎓", 
    layout="centered"
)

# Times New Roman Font ve Okunaklı Büyük Punto
st.markdown("""
    <style>
        html, body, p, span, label, div, [class*="st-"] {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 20px !important;
        }
        h1, h2, h3 {
            font-family: 'Times New Roman', Times, serif !important;
            font-weight: bold !important;
        }
        h1 { font-size: 32px !important; }
        h2, h3 { font-size: 24px !important; }
        .stButton button {
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 20px !important;
            padding: 10px 20px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 Akademik Sınav ve Test Asistanı")
st.write("Ders slaytınızı (PDF) yükleyin; yapay zeka sınav düzeyinde resmi sorular hazırlasın.")

raw_api_key = st.text_input("Google Gemini API Anahtarınızı Girin:", type="password")
uploaded_file = st.file_uploader("Ders Notunu Yükle (PDF)", type="pdf")

if "sorular" not in st.session_state:
    st.session_state.sorular = None

def hizli_ses_oynat(metin):
    if not HAS_TTS:
        return
    try:
        tts = gTTS(text=metin, lang='tr')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64_audio = base64.b64encode(fp.read()).decode('utf-8')
        html_code = (
            '<audio id="tts_audio" autoplay controls style="width:100%;">'
            f'<source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">'
            '</audio><script>var a=document.getElementById("tts_audio"); if(a) a.playbackRate=1.25;</script>'
        )
        components.html(html_code, height=70)
    except Exception:
        pass

if uploaded_file is not None and raw_api_key:
    if st.button("🚀 Testi Hazırla"):
        clean_key = raw_api_key.strip()
        if not clean_key:
            st.error("Geçersiz API Anahtarı!")
            st.stop()

        with st.spinner("Ders notu inceleniyor ve sorular hazırlanıyor..."):
            try:
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
                    "Sen üniversite vize/final düzeyinde akademik sınav soruları hazırlayan uzman bir koçsun. "
                    "Aşağıdaki ders slaytından resmi dille yazılmış, orta-zor düzeyde 3 adet 5 şıklı çoktan seçmeli soru oluştur.\n\n"
                    "SADECE aşağıdaki JSON formatında çıktı ver:\n[\n  {\n"
                    '    "soru": "Soru metni...",\n'
                    '    "A": "A şıkkı", "B": "B şıkkı", "C": "C şıkkı", "D": "D şıkkı", "E": "E şıkkı",\n'
                    '    "dogru_cevap": "A",\n'
                    '    "dogru_tepki": "Tebrikler, doğru yanıt!",\n'
                    '    "yanlis_tepki": "Maalesef yanlış yanıt.",\n'
                    '    "puf_noktasi": "Akademik Püf Noktası: ..."\n'
                    "  }\n]\n\nDers Notu:\n" + text
                )

                response_text = None
                last_error_msg = ""
                candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]

                if USE_NEW_SDK:
                    client = genai.Client(api_key=clean_key)
                    for model_name in candidate_models:
                        for attempt in range(2):
                            try:
                                res = client.models.generate_content(
                                    model=model_name,
                                    contents=prompt
                                )
                                if res and res.text:
                                    response_text = res.text
                                    break
                            except Exception as ex:
                                last_error
