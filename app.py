import os
import streamlit as st
from groq import Groq
import yt_dlp
from fpdf import FPDF

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="EduExtract — AI Конспекты и Тесты (Groq)",
    page_icon="🎓",
    layout="wide"
)

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С АУДИО И ИИ ---

def download_youtube_audio(url):
    for f in os.listdir('.'):
        if f.startswith('temp_audio'):
            try:
                os.remove(f)
            except Exception:
                pass

    ydl_opts = {
        'format': 'ba[ext=m4a]/ba/worstaudio',
        'outtmpl': 'temp_audio.m4a',
        'quiet': True,
        'no_warnings': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    for file in os.listdir('.'):
        if file.startswith('temp_audio'):
            return file
    return None

def transcribe_audio_with_groq(client, audio_path):
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="text"
        )
    return transcription

def generate_ai_content(client, prompt, text):
    # Обрезаем текст до первых 15 000 символов для соблюдения контекстного лимита
    truncated_text = text[:15000] if len(text) > 15000 else text
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты — эксперт-методист. Отвечай четко, структурированно, используя Markdown на языке исходного текста."},
            {"role": "user", "content": f"{prompt}\n\nТекст лекции:\n{truncated_text}"}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

def create_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    
    safe_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=safe_text)
    
    return bytes(pdf.output())

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---

st.title("🎓 EduExtract — Умный аналитик видео и лекций (Groq AI)")
st.caption("Превращайте любые видео с YouTube и аудиозаписи в конспекты, тесты и глоссарии.")

# Боковое меню
st.sidebar.header("⚙️ Настройки доступа")
groq_api_key = st.sidebar.text_input("Введите ваш Groq API Key:", type="password")
st.sidebar.info("💡 Ключ можно бесплатно получить на console.groq.com")

tab1, tab2 = st.tabs(["🔗 Ссылка на YouTube", "📁 Загрузить файл (MP3, MP4)"])

# Вкладка 1: YouTube
with tab1:
    youtube_url = st.text_input("Вставьте ссылку на YouTube-видео:")
    if st.button("🚀 Обработать YouTube видео", key="yt_btn"):
        if not groq_api_key:
            st.error("Пожалуйста, введите Groq API Key в меню слева!")
        elif not youtube_url:
            st.warning("Вставьте ссылку на видео!")
        else:
            try:
                client = Groq(api_key=groq_api_key)
                with st.spinner("📥 Скачиваем аудио из видео..."):
                    audio_file = download_youtube_audio(youtube_url)
                
                if audio_file:
                    with st.spinner("🧠 Groq Whisper распознает речь..."):
                        text_result = transcribe_audio_with_groq(client, audio_file)
                        st.session_state['lecture_text'] = text_result
                        st.success("Речь успешно распознана!")
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                else:
                    st.error("Не удалось извлечь звук.")
            except Exception as e:
                st.error(f"Ошибка при транскрибации: {str(e)}")

# Вкладка 2: Файл
with tab2:
    uploaded_file = st.file_uploader("Загрузите файл", type=["mp3", "wav", "mp4", "m4a"])
    if uploaded_file and st.button("🚀 Обработать загруженный файл", key="file_btn"):
        if not groq_api_key:
            st.error("Пожалуйста, введите Groq API Key!")
        else:
            try:
                client = Groq(api_key=groq_api_key)
                file_path = f"temp_{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                with st.spinner("🧠 Groq Whisper распознает речь..."):
                    text_result = transcribe_audio_with_groq(client, file_path)
                    st.session_state['lecture_text'] = text_result
                    st.success("Файл успешно обработан!")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                st.error(f"Ошибка при обработке файла: {str(e)}")

# --- БЛОК ГЕНЕРАЦИИ МАТЕРИАЛОВ ---

if 'lecture_text' in st.session_state and st.session_state['lecture_text']:
    st.divider()
    st.subheader("📑 Извлеченный текст (Транскрипция):")
    with st.expander("Показать полный распознанный текст"):
        st.write(st.session_state['lecture_text'])

    st.subheader("🤖 Выберите, что сгенерировать:")
    
    col1, col2, col3 = st.columns(3)

    def process_generation(prompt_text):
        if not groq_api_key:
            st.error("Введите Groq API Key в боковом меню!")
            return
        try:
            client = Groq(api_key=groq_api_key)
            with st.spinner("Генерируем материал через AI..."):
                res = generate_ai_content(client, prompt_text, st.session_state['lecture_text'])
                st.session_state['result'] = res
        except Exception as e:
            st.error(f"Ошибка генерации: {str(e)}")

    with col1:
        if st.button("📝 Краткий конспект", key="btn_cons"):
            process_generation("Сделай подробный структурированный конспект этой лекции. Выдели главную тему, ключевые тезисы и выводы.")

    with col2:
        if st.button("❓ Тест для проверки", key="btn_test"):
            process_generation("Составь тест из 5 вопросов с 4 вариантами ответов (A, B, C, D) и правильными ответами в конце.")

    with col3:
        if st.button("📚 Глоссарий терминов", key="btn_gloss"):
            process_generation("Найди в тексте все ключевые термины и дай им краткие определения.")

    # Вывод результатов и скачивание PDF
    if 'result' in st.session_state and st.session_state['result']:
        st.markdown("---")
        st.markdown(st.session_state['result'])
        try:
            pdf_data = create_pdf(st.session_state['result'])
            st.download_button(
                label="📥 Скачать результат в PDF", 
                data=pdf_data, 
                file_name="EduExtract_Material.pdf", 
                mime="application/pdf"
            )
        except Exception as e:
            st.warning(f"Ошибка формирования PDF: {str(e)}")