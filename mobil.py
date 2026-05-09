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

# --- 3. KULLANICI GİRİŞ SİSTEMİ ---
if 'login' not in st.session_state:
    st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🔐 Şoför Giriş Paneli")
    
    try:
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1}))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Hata: Araçlar Yüklenemedi"]

    secili_plaka = st.selectbox("Aracınızı Seçin", plakalar)
    sifre = st.text_input("Giriş Şifresi (Plakanın Son 4 Hanesi)", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # ŞİFRE MANTIĞI: Plakadaki boşlukları siler ve son 4 haneye bakar
        temiz_plaka = secili_plaka.replace(" ", "").upper()
        dogru_sifre = temiz_plaka[-4:]
        
        if sifre == dogru_sifre:
            st.session_state['login'] = True
            st.session_state['plaka'] = secili_plaka
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error(f"Hatalı Şifre! (İpucu: {dogru_sifre})") # Hata alırsan ipucunu gör diye ekledim

else:
    # --- 4. ANA PANEL ---
    st.title(f"🚛 {st.session_state['plaka']}")
    
    tab1, tab2, tab3 = st.tabs(["📍 KM GİRİŞİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        
        # KRİTİK DÜZELTME: Plaka eşleşmesini hem boşluklu hem boşluksuz deniyoruz
        # Ayrıca "durum" alanını tamamen boşverip sadece o plakaya ait TAMAMLANMAMIŞ son seferi çekiyoruz
        aktif_sefer = db["Seferler"].find_one({
            "$or": [
                {"plaka": plaka},
                {"plaka": plaka.replace(" ", "")}
            ],
            "durum": {"$ne": "TAMAMLANDI"} # Tamamlanmamış her şeyi göster
        }, sort=[("tarih", -1)]) # En yeni olanı getir
        
        if aktif_sefer:
            st.info(f"✅ **Bulunan Sefer:** {aktif_sefer.get('guzergah', 'Rota Bilgisi Yok')}")
            # Veritabanındaki alan isimleri farklı olabilir, her ihtimali kontrol ediyoruz
            eski_km = aktif_sefer.get("depo_cikis_km") or aktif_sefer.get("cikis_km") or 0
            
            c_km = st.number_input("Depo Çıkış KM", value=float(eski_km))
            d_km = st.number_input("Dönüş KM (Sefer Sonu)", value=0.0)
            
            if st.button("KM BİLGİLERİNİ KAYDET"):
                fiili = d_km - c_km if d_km > c_km else 0
                
                # Güncelleme yaparken hem ID hem Sefer No kullanıyoruz
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {
                        "depo_cikis_km": c_km,
                        "donus_km": d_km,
                        "fiili_km": fiili,
                        "durum": "TAMAMLANDI" if d_km > 0 else "BEKLEYOR",
                        "mobil_islem_tarihi": datetime.now()
                    }}
                )
                st.success(f"Başarıyla Kaydedildi! Fiili KM: {fiili}")
        else:
            st.warning("Üzerinizde aktif bir sefer bulunamadı. Lütfen merkezden sefer tanımlandığından emin olun.")