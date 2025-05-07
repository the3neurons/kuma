import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from ocr import extract_conversation
from answer import get_answers

st.set_page_config(page_title="Kuma", layout="centered")

st.title("Kuma")

# Upload de l'image
uploaded_file: UploadedFile = st.file_uploader(
    "Importe un screenshot d'une conversation pour commencer:",
    type=["jpg", "jpeg", "png"],
)

if uploaded_file:
    image: bytes = uploaded_file.read()
    st.image(image, width=256)

    emotion: str = st.selectbox(
        "De quelle émotion devrait être la réponse ?",
        (
            "Comme le sentiment de la conversation",
            "Séduisante",
            "Agressive",
            "Marrante",
            "Professionnelle",
            "Opposée",
        ),
    )

    if st.button("Générer des réponses"):
        conversation: str = extract_conversation(image)

        answers: list[str] = get_answers(conversation, emotion)
        for answer in answers:
            st.text(answer)
