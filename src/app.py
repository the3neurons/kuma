import streamlit as st
from PIL import Image

st.set_page_config(page_title="Générateur d'expressions", layout="centered")

st.title("🎭 Générateur d'expressions à partir d'une image")

# Initialisation des états
if "styles" not in st.session_state:
    st.session_state.styles = {
        "professionnel": False,
        "flirt": False,
        "contraire": False,
        "enerve": False,
    }

# CSS pour les boutons stylés
st.markdown(
    """
    <style>
    .style-button {
        display: inline-block;
        width: 48%;
        margin: 1%;
        padding: 1em;
        font-size: 1.2em;
        border: none;
        border-radius: 10px;
        color: white;
        cursor: pointer;
        text-align: center;
    }
    .selected { box-shadow: 0 0 10px #333; }
    .pro { background-color: #0a9396; }
    .flirt { background-color: #f72585; }
    .contraire { background-color: #ffba08; color: black; }
    .enerve { background-color: #d00000; }
    form { display: inline; }
    </style>
""",
    unsafe_allow_html=True,
)

# Upload de l'image
uploaded_file = st.file_uploader("Téléverse une image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image téléversée", use_container_width=True)

    st.markdown("## Choisis un ou plusieurs styles")

    # Gestion des clics via hidden forms
    clicked = st.query_params.get("clicked", [None])[0]

    if clicked and clicked in st.session_state.styles:
        st.session_state.styles[clicked] = not st.session_state.styles[clicked]
        # Reset le paramètre URL pour éviter l'effet double clic
        st.experimental_set_query_params()

    # Génération des boutons HTML cliquables
    def style_btn(label, key, emoji, css_class):
        selected = "selected" if st.session_state.styles[key] else ""
        return f"""
            <form action="/?clicked={key}" method="get">
                <button class="style-button {css_class} {selected}" type="submit">{emoji} {label}</button>
            </form>
        """

    html_buttons = (
        style_btn("Professionnel", "professionnel", "🧑‍💼", "pro")
        + style_btn("Flirt", "flirt", "💘", "flirt")
        + style_btn("Contraire", "contraire", "🔁", "contraire")
        + style_btn("Énervé", "enerve", "😤", "enerve")
    )

    st.markdown(html_buttons, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("✨ Générer une réponse"):
        st.success("✅ Réponse générée")
        styles_choisis = [k for k, v in st.session_state.styles.items() if v]
        st.write(
            f"Styles activés : {', '.join(styles_choisis) if styles_choisis else 'Aucun'}"
        )

else:
    st.info("🖼️ Téléverse une image pour commencer.")
