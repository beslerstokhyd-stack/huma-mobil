# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse

# --- 1. BULUT BAĞLANTI AYARLARI ---
USER = "admin"
PASS = urllib.parse.quote_plus("Hs19051905")
CLUSTER = "cluster0.p1ojawz.mongodb.net"
DB_NAME = "SivasLojistikDB"
CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

@st.cache_resource
def get_db():
    try:
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
        return client[DB_NAME]
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

db = get_db()

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚛", layout="centered")

# CSS ile butonları ve arayüzü güzelleştirelim
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
        # Araçları buluttan çekiyoruz
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1}))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Hata: Araçlar Yüklenemedi"]

    secili_plaka = st.selectbox("Aracınızı Seçin", plakalar)
    sifre = st.text_input("Giriş Şifresi (Plakanın Son 4 Hanesi)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Güvenlik: Plakanın son 4 karakteri şifredir
        temiz_plaka = secili_plaka.replace(" ", "")
        dogru_sifre = temiz_plaka[-4:]
        
        if sifre == dogru_sifre:
            st.session_state['login'] = True
            st.session_state['plaka'] = secili_plaka
            st.success("Giriş Başarılı! Bekleyin...")
            st.rerun()
        else:
            st.error("Hatalı Şifre! Lütfen plakanızın son 4 hanesini girin.")

else:
    # --- 4. ANA PANEL (Giriş Yapıldı) ---
    st.title(f"🚛 {st.session_state['plaka']}")
    st.sidebar.write(f"Sürücü: {st.session_state['plaka']}")
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['login'] = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📍 KM GİRİŞİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    # --- TAB 1: KM GİRİŞİ ---
    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        aktif_sefer = db["Seferler"].find_one({"plaka": plaka, "durum": "BEKLEYOR"})
        
        if aktif_sefer:
            st.info(f"**Güncel Rota:** {aktif_sefer.get('rota_ozet', 'Rota Belirtilmemiş')}")
            c_km = st.number_input("Depo Çıkış KM", value=float(aktif_sefer.get("depo_cikis_km", 0)))
            d_km = st.number_input("Dönüş KM (Sefer Sonu)", value=float(aktif_sefer.get("donus_km", 0)))
            
            if st.button("KM BİLGİLERİNİ KAYDET"):
                fiili = d_km - c_km if d_km > c_km else 0
                yeni_durum = "TAMAMLANDI" if d_km > 0 else "BEKLEYOR"
                
                db["Seferler"].update_one(
                    {"sefer_id": aktif_sefer["sefer_id"]},
                    {"$set": {
                        "depo_cikis_km": c_km,
                        "donus_km": d_km,
                        "fiili_km": fiili,
                        "durum": yeni_durum
                    }}
                )
                st.success(f"KM Kaydedildi. Hesaplanan Fiili KM: {fiili}")
        else:
            st.warning("Üzerinizde şu an aktif (bekleyen) bir sefer görünmüyor.")

    # --- TAB 2: YAKIT ALIMI ---
    with tab2:
        st.subheader("Yakıt Alım Bilgisi")
        litre = st.number_input("Kaç Litre Alındı?", min_value=0.0)
        tutar = st.number_input("Toplam Tutar (TL)", min_value=0.0)
        istasyon = st.text_input("İstasyon / Şehir")
        
        if st.button("YAKIT FİŞİNİ GÖNDER"):
            if tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "tip": "YAKIT",
                    "miktar": litre,
                    "tutar": tutar,
                    "detay": istasyon,
                    "kaynak": "MOBIL"
                })
                st.success("Yakıt kaydı merkeze iletildi.")
            else:
                st.error("Lütfen geçerli bir tutar girin.")

    # --- TAB 3: MASRAFLAR ---
    with tab3:
        st.subheader("Harcama ve Masraf")
        m_tip = st.selectbox("Masraf Türü", ["Yemek", "Tamir", "Lastik", "Otoyol", "Diğer"])
        m_tutar = st.number_input("Harcama Tutarı (TL)", min_value=0.0)
        aciklama = st.text_area("Masraf Açıklaması")
        
        if st.button("MASRAFI KAYDET"):
            if m_tutar > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "tip": "MASRAF",
                    "kategori": m_tip,
                    "tutar": m_tutar,
                    "aciklama": aciklama,
                    "kaynak": "MOBIL"
                })
                st.success("Masraf kaydı başarıyla oluşturuldu.")
            else:
                st.error("Lütfen tutar giriniz.")