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
        with st.spinner("Asistan aktif modelleri sorguluyor ve slaytı inceliyor..."):
            try:
                # API Anahtarını Ayarla
                genai.configure(api_key=api_key.strip())
                
                # Google API'den doğrudan aktif modelleri canlı listele
                active_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        active_models.append(m.name)
                
                if not active_models:
                    st.error("API anahtarınızla erişilebilen aktif bir model bulunamadı. Lütfen API anahtarınızı kontrol edin.")
                    st.stop()
                
                # Öncelikli olarak 'flash' barındıran tam model ismini seç
                selected_model_name = None
                for m_name in active_models:
                    if 'flash' in m_name.lower():
                        selected_model_name = m_name
                        break
                
                if not selected_model_name:
                    selected_model_name = active_models[0]

                # Seçilen canlı model ile başlat
                model = genai.GenerativeModel(selected_model_name)
                
                # PDF Metnini Çıkarma
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
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

                response = model.generate_content(prompt)
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
                
                st.info(
