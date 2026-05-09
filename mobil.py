# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse

# --- 1. BULUT BAĞLANTI AYARLARI ---
# Önceki bağlantı hatalarını gidermek için adres güncellendi
USER = "beslerstokhyd"
PASS = urllib.parse.quote_plus("Asdfgh123.")
CLUSTER = "cluster0.v8v6f.mongodb.net"
DB_NAME = "SivasLojistikDB"

CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0"

@st.cache_resource
def get_db():
    try:
        # tlsAllowInvalidCertificates=True ekleyerek SSL hatalarını bypass ediyoruz
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where(), tlsAllowInvalidCertificates=True)
        return client[DB_NAME]
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

db = get_db()

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚚", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #2ecc71; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KULLANICI GİRİŞ SİSTEMİ ---
if 'login' not in st.session_state:
    st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🔐 Şoför Giriş Paneli")
    st.write("Hüma Lojistik Sistemine Hoş Geldiniz.")
    
    try:
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1}))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Yükleniyor..."]

    secili_plaka = st.selectbox("Aracınızı Seçin", plakalar)
    sifre = st.text_input("Giriş Şifresi (Plakanın Son 4 Hanesi)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Boşlukları temizle ve son 4 haneyi kontrol et
        temiz_plaka = secili_plaka.replace(" ", "")
        dogru_sifre = temiz_plaka[-4:]
        
        if sifre == dogru_sifre:
            st.session_state['login'] = True
            st.session_state['plaka'] = secili_plaka
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error("Hatalı Şifre!")

else:
    # --- 4. ANA PANEL ---
    st.title(f"🚛 {st.session_state['plaka']}")
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['login'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📍 KM GİRİŞİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    # --- TAB 1: KM GİRİŞİ ---
    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        
        # SEFERLERİN DÜŞMESİ İÇİN: Durum kontrolünü genişlettik (BEKLEYOR veya BEKLEMEDE)
        # Ayrıca plaka eşleşmesini büyük/küçük harf duyarsız yaptık
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": plaka.replace(" ", ""), "$options": "i"},
            "durum": {"$in": ["BEKLEYOR", "BEKLEMEDE", "AKTİF"]}
        })
        
        if aktif_sefer:
            st.info(f"✅ **Aktif Sefer:** {aktif_sefer.get('guzergah', 'Rota Belirtilmemiş')}")
            c_km = st.number_input("Çıkış KM", value=float(aktif_sefer.get("depo_cikis_km", 0)))
            d_km = st.number_input("Dönüş KM", value=float(aktif_sefer.get("donus_km", 0)))
            
            if st.button("KM BİLGİLERİNİ KAYDET"):
                fiili = d_km - c_km if d_km > c_km else 0
                # Eğer dönüş KM girilmişse seferi tamamla
                yeni_durum = "TAMAMLANDI" if d_km > 0 else aktif_sefer["durum"]
                
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {
                        "depo_cikis_km": c_km,
                        "donus_km": d_km,
                        "fiili_km": fiili,
                        "durum": yeni_durum,
                        "son_guncelleme": datetime.now()
                    }}
                )
                st.success(f"Kaydedildi. Fiili KM: {fiili}")
        else:
            st.warning("Üzerinizde şu an aktif bir sefer görünmüyor.")

    # --- TAB 2 & 3: YAKIT VE MASRAF (Aynı mantıkla devam eder) ---
    with tab2:
        st.subheader("Yakıt Girişi")
        litre = st.number_input("Litre", min_value=0.0)
        tutar = st.number_input("Tutar (TL)", min_value=0.0)
        if st.button("YAKIT KAYDET"):
            db["Giderler"].insert_one({"tarih": datetime.now(), "plaka": plaka, "tip": "YAKIT", "tutar": tutar, "miktar": litre})
            st.success("Kaydedildi.")

    with tab3:
        st.subheader("Masraf Girişi")
        m_tutar = st.number_input("Masraf Tutarı", min_value=0.0)
        if st.button("MASRAF KAYDET"):
            db["Giderler"].insert_one({"tarih": datetime.now(), "plaka": plaka, "tip": "MASRAF", "tutar": m_tutar})
            st.success("Kaydedildi.")