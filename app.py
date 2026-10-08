"""CodeAlpha AI Internship - Task 1: Language Translation Tool
UI: Streamlit | Translation: Google Translate (via deep-translator) | Speech: gTTS
"""
import io
import re
import time

import streamlit as st
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS
from gtts.lang import tts_langs
from langdetect import detect

MAX_CHARS = 5000
AUTO = "Auto Detect"

st.set_page_config(page_title="Language Translator", page_icon="🌐", layout="centered")


@st.cache_data(show_spinner=False)
def get_languages() -> dict:
    """Return {Language Name: code}. Falls back to a small list if offline."""
    try:
        langs = GoogleTranslator().get_supported_languages(as_dict=True)
        return {name.title(): code for name, code in langs.items()}
    except Exception:
        return {"English": "en", "Spanish": "es", "French": "fr",
                "German": "de", "Hindi": "hi", "Bengali": "bn", "Arabic": "ar"}


@st.cache_data(show_spinner=False)
def speech_languages() -> set:
    try:
        return set(tts_langs().keys())
    except Exception:
        return set()


def text_to_speech(text: str, lang: str) -> bytes:
    buf = io.BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(buf)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def mymemory_codes() -> list:
    return list(MyMemoryTranslator(source="en-GB", target="fr-FR")
                .get_supported_languages(as_dict=True).values())


def to_mymemory_code(code: str):
    """Convert a Google-style code ('fr') to MyMemory's style ('fr-FR')."""
    codes = mymemory_codes()
    if code in codes:
        return code
    prefix = code.split("-")[0].lower()
    if prefix == "en":
        return "en-GB"
    matches = [c for c in codes if c.lower().startswith(prefix + "-")]
    main = [c for c in matches if c.split("-")[1].lower() == prefix]  # fr-FR, de-DE
    return (main or matches or [None])[0]


def split_chunks(text: str, limit: int = 450) -> list:
    """MyMemory accepts max 500 chars per request, so split on sentence ends."""
    parts = re.split(r"(?<=[.!?\u0964\n])\s+", text.strip())
    chunks, current = [], ""
    for part in parts:
        while len(part) > limit:  # very long sentence: hard split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(part[:limit])
            part = part[limit:]
        if len(current) + len(part) + 1 <= limit:
            current = f"{current} {part}".strip()
        else:
            chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def translate_with_mymemory(text: str, src: str, tgt: str) -> str:
    if src == "auto":
        src = detect(text)  # local language detection
        if src.startswith("zh"):
            src = "zh-CN" if src == "zh-cn" else "zh-TW"
    src_mm, tgt_mm = to_mymemory_code(src), to_mymemory_code(tgt)
    if not src_mm or not tgt_mm:
        raise ValueError("Language not supported by the backup translator.")
    if src_mm == tgt_mm:
        return text
    translator = MyMemoryTranslator(source=src_mm, target=tgt_mm)
    return " ".join(translator.translate(chunk) for chunk in split_chunks(text))


def translate_text(text: str, src: str, tgt: str) -> str:
    """Try Google (one retry); if blocked, fall back to MyMemory."""
    google_error = None
    for attempt in range(2):
        try:
            return GoogleTranslator(source=src, target=tgt).translate(text)
        except Exception as e:  # rate limit, network, etc.
            google_error = e
            if attempt == 0:
                time.sleep(2)
    try:
        return translate_with_mymemory(text, src, tgt)
    except Exception as backup_error:
        raise RuntimeError(f"Google: {google_error} | Backup: {backup_error}")


def swap_languages():
    src, tgt = st.session_state.src, st.session_state.tgt
    if src == AUTO:
        st.session_state.swap_warning = True
        return
    st.session_state.src, st.session_state.tgt = tgt, src
    st.session_state.swap_warning = False


languages = get_languages()
names = sorted(languages)

st.session_state.setdefault("src", AUTO)
st.session_state.setdefault("tgt", "English" if "English" in names else names[0])
st.session_state.setdefault("result", None)

st.title("🌐 Language Translator")
st.caption("Type or paste text, choose languages, and translate.")

col1, col2, col3 = st.columns([5, 1, 5])
with col1:
    st.selectbox("From", [AUTO] + names, key="src")
with col2:
    st.write("")
    st.write("")
    st.button("⇄", on_click=swap_languages, help="Swap languages")
with col3:
    st.selectbox("To", names, key="tgt")

if st.session_state.get("swap_warning"):
    st.warning("Pick a specific source language to swap.")

text = st.text_area("Text to translate", height=160, max_chars=MAX_CHARS,
                    placeholder="Enter text here...")
st.caption(f"{len(text)}/{MAX_CHARS} characters")

if st.button("Translate", type="primary", use_container_width=True):
    if not text.strip():
        st.warning("Please enter some text first.")
    elif st.session_state.src == st.session_state.tgt:
        st.info("Source and target languages are the same.")
    else:
        src_code = "auto" if st.session_state.src == AUTO else languages[st.session_state.src]
        tgt_code = languages[st.session_state.tgt]
        try:
            with st.spinner("Translating..."):
                out = translate_text(text, src_code, tgt_code)
            st.session_state.result = {"text": out, "lang": tgt_code}
        except Exception as e:
            st.session_state.result = None
            st.error("Translation failed. You may be rate-limited by Google or offline. "
                     f"Wait a minute, turn off any VPN, and try again.\n\nDetails: {e}")

result = st.session_state.result
if result:
    st.subheader("Translation")
    # st.code shows a built-in copy button on hover
    st.code(result["text"], language=None, wrap_lines=True)

    if result["lang"] in speech_languages():
        if st.button("🔊 Listen"):
            try:
                st.audio(text_to_speech(result["text"], result["lang"]), format="audio/mp3")
            except Exception as e:
                st.error(f"Text-to-speech failed: {e}")
    else:
        st.caption("Text-to-speech isn't available for this language.")