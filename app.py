import base64
import io
import json
import re
import time
import PyPDF2
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from gtts import gTTS

st.set_page_config(page_title="Akademik Sınav Asistanı", page_icon="🎓", layout="centered")

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
    try:
        tts = gTTS(text=metin, lang='tr')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64_audio = base64.b64encode(fp.read()).decode('utf-8')
        html_code = f'<audio id="tts_audio" autoplay controls style="width:100%;"><source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3"></audio><script>var a=document.getElementById("tts_audio"); if(a) a.playbackRate=1.25;</script>'
        components.html(html_code, height=70)
    except Exception:
        pass

def get_gemini_response(api_key, prompt_text):
    client = genai.Client(api_key=api_key)
    models = ["gemini-1.5-flash", "gemini-2.5-flash"]
    last_error = ""
    for m in models:
        for _ in range(2):
            try:
                res = client.models.generate_content(model=m, contents=prompt_text)
                if res and res.text:
                    return res.text
            except Exception as e:
                last_error = str(e)
                time.sleep(1.5)
    raise Exception(f"Sunucu yoğunluğu veya bağlantı hatası: {last_error}")

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
                    
                prompt = (
                    "Sen üniversite vize ve final düzeyinde akademik sınav soruları hazırlayan uzman bir eğitmensin. "
                    "Aşağıdaki ders slaytından tamamen resmi dille yazılmış, orta-zor düzeyde 3 adet 5 şıklı çoktan seçmeli soru oluştur.\n\n"
                    "SADECE aşağıdaki JSON formatında çıktı ver:\n[\n  {\n"
                    '    "soru": "Soru metni...",\n'
                    '    "A": "A şıkkı", "B": "B şıkkı", "C": "C şıkkı", "D": "D şıkkı", "E": "E şıkkı",\n'
                    '    "dogru_cevap": "A",\n'
                    '    "dogru_tepki": "Tebrikler, soruyu doğru yanıtladınız.",\n'
                    '    "yanlis_tepki": "Maalesef yanlış yanıt.",\n'
                    '    "puf_noktasi": "Akademik Püf Noktası: ..."\n'
                    "  }\n]\n\nDers Notu:\n" + text[:15000]
                )
                
                response_text = get_gemini_response(clean_key, prompt)
                
                raw_txt = response_text.strip()
                json_match = re.search(r"\[\s*\{.*\}\s*\]", raw_txt, re.DOTALL)
                json_str = json_match.group(0) if json_match else raw_txt.replace("```json", "").replace("```", "").strip()
                
                st.session_state.sorular = json.loads(json_str)
                st.success("Sınav soruları ve sesli açıklamalar hazır!")
                
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")

if st.session_state.sorular:
    st.write("---")
    for i, q in enumerate(st.session_state.sorular):
        st.subheader(f"Soru {i+1}")
        st.write(q["soru"])
        
        secenekler = [f"A) {q['A']}", f"B) {q['B']}", f"C) {q['C']}", f"D) {q['D']}", f"E) {q['E']}"]
        secim = st.radio("Cevabınız:", secenekler, key=f"rad_{i}", index=None)
        
        if st.button("Cevabı Kontrol Et 🔊", key=f"btn_{i}"):
            if secim:
                secilen = secim.split(")")[0]
                if secilen == q["dogru_cevap"]:
                    st.success(f"✅ {q['dogru_tepki']}")
                    ses = f"{q['dogru_tepki']} {q['puf_noktasi']}"
                else:
                    st.error(f"❌ {q['yanlis_tepki']} (Doğru Cevap: {q['dogru_cevap']})")
                    ses = f"{q['yanlis_tepki']} Doğru cevap {q['dogru_cevap']} şıkkıdır. {q['puf_noktasi']}"
                    
                st.info(f"💡 **Sınav Püf Noktası:** {q['puf_noktasi']}")
                hizli_ses_oynat(ses)
            else:
                st.warning("Lütfen bir seçenek işaretleyin.")
        st.write("---")
