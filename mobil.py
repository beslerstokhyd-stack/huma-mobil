# -*- coding: utf-8 -*-
import streamlit as st
from pymongo import MongoClient
import certifi
from datetime import datetime
import urllib.parse

# --- 1. BULUT BAĞLANTI AYARLARI ---
# NOT: Masaüstü uygulaman hangi MongoDB'ye bağlanıyorsa buraya onu yazmalısın.
# Eğer Masaüstü de bu adrese bağlanıyorsa sorun yok.
USER = "admin"
PASS = urllib.parse.quote_plus("Hs19051905")
CLUSTER = "cluster0.p1ojawz.mongodb.net"
DB_NAME = "SivasLojistikDB"
CONNECTION_STRING = f"mongodb+srv://{USER}:{PASS}@{CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"

@st.cache_resource
def get_db():
    try:
        # Masaüstü kodunda olduğu gibi bağlantıyı kuruyoruz
        client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
        return client[DB_NAME]
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

db = get_db()

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="Hüma Lojistik Mobil", page_icon="🚛", layout="centered")

# --- 3. KULLANICI GİRİŞ SİSTEMİ ---
if 'login' not in st.session_state:
    st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🔐 Şoför Giriş Paneli")
    
    try:
        # Araç listesini çek
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1}))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Hata: Araçlar Yüklenemedi"]

    secili_plaka = st.selectbox("Aracınızı Seçin", plakalar)
    sifre = st.text_input("Giriş Şifresi (Plakanın Son 4 Hanesi)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Şifre kontrolü (Masaüstü gibi plakayı temizleyip bakıyoruz)
        temiz_plaka = secili_plaka.replace(" ", "").upper()
        dogru_sifre = temiz_plaka[-4:]
        
        if sifre == dogru_sifre:
            st.session_state['login'] = True
            st.session_state['plaka'] = secili_plaka
            st.rerun()
        else:
            st.error("Hatalı Şifre!")

else:
    # --- 4. ANA PANEL ---
    st.title(f"🚛 {st.session_state['plaka']}")
    
    tab1, tab2, tab3 = st.tabs(["📍 KM GİRİŞİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        
        # --- KRİTİK UYUM GÜNCELLEMESİ ---
        # Masaüstü kodun durumu "BEKLEMEDE" olarak kaydediyor.
        # Ayrıca plakayı "58ABC123" (boşluksuz) formatında aratıyoruz.
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": plaka.replace(" ", ""), "$options": "i"},
            "durum": "BEKLEMEDE" 
        }, sort=[("kayit_tarihi", -1)]) # En son eklenen seferi getir
        
        if aktif_sefer:
            # Masaüstü kodunda duraklar "guzergah_detay" olarak metin formatında geliyor
            rota = aktif_sefer.get('guzergah_detay', "Rota Bilgisi Yok")
            st.info(f"✅ **Güzergah:** {rota}")
            
            c_km = st.number_input("Depo Çıkış KM", value=0.0)
            d_km = st.number_input("Dönüş KM (Sefer Sonu)", value=0.0)
            
            if st.button("KM BİLGİLERİNİ KAYDET"):
                fiili = d_km - c_km if d_km > c_km else 0
                
                # Güncelleme: Durumu TAMAMLANDI yapıyoruz
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {
                        "depo_cikis_km": c_km,
                        "donus_km": d_km,
                        "fiili_km": fiili,
                        "durum": "TAMAMLANDI" if d_km > 0 else "BEKLEMEDE",
                        "mobil_onay_tarihi": datetime.now()
                    }}
                )
                st.success(f"Kaydedildi! Fiili Mesafe: {fiili} KM")
        else:
            st.warning("Üzerinizde 'BEKLEMEDE' olan bir sefer bulunamadı.")