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
        # Araç listesini çek
        araclar_data = list(db["Araclar"].find({}, {"plaka": 1, "sifre": 1}))
        plakalar = [a["plaka"] for a in araclar_data]
    except:
        plakalar = ["Hata: Veritabanına ulaşılamadı"]

    secili_plaka = st.selectbox("Aracınızı Seçin", plakalar)
    girilen_sifre = st.text_input("Giriş Şifresi", type="password")
    
    if st.button("SİSTEME GİRİŞ YAP"):
        # Seçilen aracı bul
        hedef_arac = next((a for a in araclar_data if a["plaka"] == secili_plaka), None)
        
        if hedef_arac:
            # KRİTİK GÜNCELLEME: Hem veritabanındaki hem girilen şifreyi string (metin) yapıp karşılaştırıyoruz
            db_sifre = str(hedef_arac.get("sifre", "")).strip()
            # Eğer PC'de şifre boşsa veya girilenle eşleşiyorsa
            if db_sifre == str(girilen_sifre).strip():
                st.session_state['login'] = True
                st.session_state['plaka'] = secili_plaka
                st.rerun()
            else:
                st.error(f"Hatalı Şifre! (PC'deki kayıtlı şifre ile eşleşmiyor)")
        else:
            st.error("Araç bilgisi bulunamadı.")

else:
    # --- 4. ANA PANEL ---
    st.title(f"🚛 {st.session_state['plaka']}")
    
    tab1, tab2, tab3 = st.tabs(["📍 KM GİRİŞİ", "⛽ YAKIT ALIMI", "💰 MASRAF YAZ"])
    plaka = st.session_state['plaka']

    with tab1:
        st.subheader("Sefer Kilometre Takibi")
        # Masaüstüyle uyumlu plaka formatı (Boşluksuz arama)
        temiz_plaka = plaka.replace(" ", "").upper()
        aktif_sefer = db["Seferler"].find_one({
            "plaka": {"$regex": temiz_plaka, "$options": "i"},
            "durum": "BEKLEMEDE" 
        }, sort=[("kayit_tarihi", -1)])
        
        if aktif_sefer:
            st.info(f"✅ Güzergah: {aktif_sefer.get('guzergah_detay', 'Bilinmiyor')}")
            c_km = st.number_input("Depo Çıkış KM", value=0.0)
            d_km = st.number_input("Dönüş KM (Sefer Sonu)", value=0.0)
            
            if st.button("KM BİLGİLERİNİ KAYDET"):
                fiili = d_km - c_km if d_km > c_km else 0
                db["Seferler"].update_one(
                    {"_id": aktif_sefer["_id"]},
                    {"$set": {"depo_cikis_km": c_km, "donus_km": d_km, "fiili_km": fiili, "durum": "TAMAMLANDI"}}
                )
                st.success("Bilgiler başarıyla kaydedildi.")
        else:
            st.warning("Beklemede olan bir sefer bulunamadı.")

    with tab2:
        st.subheader("Yakıt Alım Girişi")
        # OTOMATİK HESAPLAMA SİSTEMİ
        col1, col2 = st.columns(2)
        with col1:
            yakit_lt = st.number_input("Litre", min_value=0.0, step=0.1)
        with col2:
            birim_fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.0, step=0.01)
        
        toplam_tutar = round(yakit_lt * birim_fiyat, 2)
        st.metric("Toplam Tutar", f"{toplam_tutar} ₺")
        
        istasyon = st.text_input("İstasyon / Şehir Bilgisi")
        
        if st.button("YAKIT KAYDINI ONAYLA"):
            if yakit_lt > 0 and birim_fiyat > 0:
                db["Giderler"].insert_one({
                    "tarih": datetime.now(),
                    "plaka": plaka,
                    "tip": "YAKIT",
                    "miktar": yakit_lt,
                    "birim_fiyat": birim_fiyat,
                    "tutar": toplam_tutar,
                    "detay": istasyon,
                    "kaynak": "MOBIL"
                })
                st.success("Yakıt kaydı gönderildi.")
            else:
                st.error("Lütfen miktar ve fiyat giriniz.")

    with tab3:
        st.subheader("Masraf Girişi")
        m_tip = st.selectbox("Masraf Tipi", ["Yemek", "Otoyol/Köprü", "Tamir", "Diğer"])
        m_tutar = st.number_input("Tutar (TL)", min_value=0.0)
        aciklama = st.text_area("Açıklama / Detay")
        
        if st.button("MASRAFI GÖNDER"):
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
                st.success("Masraf kaydı veritabanına işlendi.")