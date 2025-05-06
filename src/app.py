import streamlit as st
from PIL import Image
from PIL.ImageFile import ImageFile
from streamlit.runtime.uploaded_file_manager import UploadedFile

st.set_page_config(page_title="Kuma", layout="centered")

st.title("Kuma")

# Upload de l'image
uploaded_file: UploadedFile = st.file_uploader(
    "Import un screenshot d'une conversation pour commencer:",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:
    image: ImageFile = Image.open(uploaded_file)
    st.image(image, width=256)

    emotion: str = st.selectbox(
        "Quelle emotion devrait être la réponse ?",
        (
            "Comme le sentiment de la conversation",
            "Séduisante",
            "Agressive",
            "Marrante",
            "Professionnelle",
            "Opposée"
        )
    )

    if st.button("Générer des réponses"):
        st.text(emotion)
        # TODO: pass the image to the extract_conversation function
