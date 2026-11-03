import streamlit as st
import google.generativeai as genai
import PyPDF2
import json

try:
    from gtts import gTTS
    import io
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

st.set_page_config(page_title="Educato Sınav Asistanı", page_icon="💊", layout="centered")

st.title("💊 Educato Tarzı Sesli Sınav Asistanı")
st.write("Slaytını yükle; esprili sesli asistan seni sınava hazırlasın!")

api_key = st.text_input("Google Gemini API Anahtarınızı Girin:", type="password")
uploaded_file = st.file_uploader("Ders Notunu Yükle (PDF)", type="pdf")

if "sorular" not in st.session_state:
    st.session_state.sorular = None

def metni_seslendir(metin):
    """Metni Türkçe ses dosyasına dönüştürür."""
    if not HAS_TTS:
        return None
    try:
        tts = gTTS(text=metin, lang='tr')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

if uploaded_file is not None and api_key:
    if st.button("🚀 Testi Hazırla"):
        with st.spinner("Asistan slaytları inceliyor ve lafları hazırlıyor..."):
            try:
                genai.configure(api_key=api_key)
                
                # PDF Metnini Çıkarma
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += (page.extract_text() or "") + "\n"
                text = text[:15000]

                # Educato Tarzı Esprili & Argolu Prompt
                prompt = f"""
                Sen Educato tarzında, öğrenci diliyle konuşan, çok esprili, hafif argolu, samimi, komik ama bilgili bir sınav koçusun.
                Aşağıdaki ders slaytını okuyarak 3 adet 5 şıklı çoktan seçmeli soru oluştur.
                
                Cevaplar için şunları hazırla:
                1. "dogru_tepki": Öğrenci doğru bilirse onu gaza getirecek komik, hafif argolu tebrik cümlesi.
                2. "yanlis_tepki": Öğrenci yanlış yaparsa tatlı-sert dalga geçecek ("Kanka naptın ya...", "Bu soru vizede çıksa patlardın" gibi) esprili eleştiri.
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
                        "puf_noktasi": "Püf Noktası: Bu mekanizmayı unutma, hoca kesin buradan vurur!"
                    }}
                ]
                
                Ders Notu:
                {text}
                """

                # Google'ın önerdiği modelleri sırayla deneyen koruma döngüsü
                candidate_models = [
                    'gemini-3.8-flash',
                    'gemini-1.5-flash',
                    'gemini-2.0-flash',
                    'gemini-1.5-pro'
                ]

                response = None
                last_error = None

                for model_name in candidate_models:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        if response and response.text:
                            break
                    except Exception as e:
                        last_error = e
                        continue

                if not response:
                    raise Exception(f"Modellere bağlanılamadı. Hata: {last_error}")

                cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                st.session_state.sorular = json.loads(cleaned_text)
                st.success("Test ve sesli yanıtlar hazır!")
                
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

# Soruları ve Sesli Asistanı Gösterme
if st.session_state.sorular:
    st.write("---")
    for i, q in enumerate(st.session_state.sorular):
        st.subheader(f"Soru {i+1}")
        st.write(q["soru"])
        
        secenekler = [f"A) {q['A']}", f"B) {q['B']}", f"C) {q['C']}", f"D) {q['D']}", f"E) {q['E']}"]
        secim = st.radio("Cevabınız:", secenekler, key=f"soru_{i}", index=None)
        
        if st.button("Cevabı Kontrol Et 🔊", key=f"btn_{i}"):
            if secim:
                secilen_harf = secim.split(")")[0]
                if secilen_harf == q["dogru_cevap"]:
                    st.success(f"✅ {q['dogru_tepki']}")
                    ses_metni = f"{q['dogru_tepki']} {q['puf_noktasi']}"
                else:
                    st.error(f"❌ {q['yanlis_tepki']} (Doğru Cevap: {q['dogru_cevap']})")
                    ses_metni = f"{q['yanlis_tepki']} Doğru cevap {q['dogru_cevap']} şıkkıydı. {q['puf_noktasi']}"
                
                st.info(f"💡 **Taktik / Püf Noktası:** {q['puf_noktasi']}")
                
                audio_file = metni_seslendir(ses_metni)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3", autoplay=True)
            else:
                st.warning("Önce bir şık seç kanka!")
        st.write("---")
