import streamlit as st
import google.generativeai as genai
import PyPDF2
import json

st.set_page_config(page_title="Eczacılık Sınav Asistanı", page_icon="💊", layout="centered")

st.title("💊 Educato Benzeri Sınav Asistanı")
st.write("Ders slaytını (PDF) yükle, yapay zeka senin için test hazırlasın.")

api_key = st.text_input("Google Gemini API Anahtarınızı Girin:", type="password")
uploaded_file = st.file_uploader("Ders Notunu Yükle (PDF formatında)", type="pdf")

if "sorular" not in st.session_state:
    st.session_state.sorular = None

if uploaded_file is not None and api_key:
    if st.button("Soruları Hazırla"):
        with st.spinner("Slaytlar okunuyor ve sorular hazırlanıyor..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                text = text[:15000]

                prompt = f"""
                Sen zorlu eczacılık sınavlarına hazırlayan uzman bir asistansın.
                Aşağıdaki ders notu metnini okuyarak öğrencilere yönelik zorlayıcı 3 adet 5 şıklı çoktan seçmeli soru hazırla.
                Çıktıyı SADECE ve kesinlikle aşağıdaki JSON formatında ver, başka hiçbir metin ekleme:
                [
                    {{"soru": "Soru metni", "A": "A şıkkı", "B": "B şıkkı", "C": "C şıkkı", "D": "D şıkkı", "E": "E şıkkı", "dogru_cevap": "A", "aciklama": "Neden bu şıkkın doğru olduğuna dair detaylı slayt açıklaması"}}
                ]
                Ders Notu:
                {text}
                """
                
                response = model.generate_content(prompt)
                cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                st.session_state.sorular = json.loads(cleaned_text)
                st.success("Sorular hazırlandı!")
                
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")

if st.session_state.sorular:
    st.write("---")
    for i, q in enumerate(st.session_state.sorular):
        st.subheader(f"Soru {i+1}")
        st.write(q["soru"])
        
        secenekler = [f"A) {q['A']}", f"B) {q['B']}", f"C) {q['C']}", f"D) {q['D']}", f"E) {q['E']}"]
        secim = st.radio("Cevabınız:", secenekler, key=f"soru_{i}", index=None)
        
        if st.button("Cevabı Kontrol Et", key=f"btn_{i}"):
            if secim:
                secilen_harf = secim.split(")")[0]
                if secilen_harf == q["dogru_cevap"]:
                    st.success("✅ Doğru Bildin!")
                else:
                    st.error(f"❌ Yanlış. Doğru Cevap: {q['dogru_cevap']}")
                st.info(f"**Açıklama:** {q['aciklama']}")
            else:
                st.warning("Lütfen bir şık seçin.")
        st.write("---")
